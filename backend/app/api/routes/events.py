"""Events endpoints — database-backed event listing and detail."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.database import get_db
from app.models import RiskSignal, Document, DocumentEntity, Entity

router = APIRouter(tags=["events"])


def _signal_to_dict(signal: RiskSignal) -> dict:
    """Convert a RiskSignal ORM object to API response dict."""
    doc = signal.document
    entities = []
    if doc and doc.document_entities:
        for de in doc.document_entities:
            ent = de.entity
            entities.append({
                "canonical_name": ent.canonical_name,
                "ticker": ent.ticker,
                "type": ent.entity_type,
                "confidence": de.confidence,
            })

    return {
        "signal_id": signal.id,
        "document_id": signal.document_id,
        "timestamp": signal.created_at.isoformat() if signal.created_at else "",
        "source": {
            "type": signal.source_type or "",
            "name": signal.source_name or "",
            "url": doc.source_url if doc else None,
        },
        "text": doc.original_text if doc else "",
        "entities": entities,
        "sentiment": {
            "label": signal.sentiment_label,
            "score": signal.sentiment_score,
            "confidence": signal.sentiment_confidence,
            "probabilities": signal.sentiment_probabilities or {},
        },
        "event": {
            "class": signal.event_class,
            "confidence": signal.event_confidence,
        },
        "impact": {
            "score": signal.impact_score,
            "risk_level": signal.risk_level,
            "components": signal.impact_components or {},
            "explanation": signal.explanation[-1] if signal.explanation else "",
        },
        "novelty_score": signal.novelty_score,
        "corroboration_score": signal.corroboration_score,
        "confidence_score": signal.overall_confidence,
        "risk_trajectory": signal.risk_trajectory,
        "explanation": signal.explanation or [],
        "processing_time_ms": signal.processing_time_ms,
        "status": signal.status,
        "cluster_id": signal.event_cluster_id,
        "market_context_available": signal.market_context_available,
        "source_credibility": signal.source_credibility,
        "stress_test": {
            "triggered": signal.impact_score >= 7.0,
            "scenario": None,
        },
    }


@router.get("/events")
def list_events(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    event_class: str | None = Query(default=None),
    risk_level: str | None = Query(default=None),
    source_type: str | None = Query(default=None),
    sentiment: str | None = Query(default=None),
    search: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> dict:
    query = db.query(RiskSignal).join(Document)

    if event_class:
        query = query.filter(RiskSignal.event_class == event_class)
    if risk_level:
        query = query.filter(RiskSignal.risk_level == risk_level)
    if source_type:
        query = query.filter(RiskSignal.source_type == source_type)
    if sentiment:
        query = query.filter(RiskSignal.sentiment_label == sentiment)
    if search:
        query = query.filter(Document.original_text.ilike(f"%{search}%"))

    total = query.count()
    signals = (
        query.order_by(desc(RiskSignal.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "items": [_signal_to_dict(s) for s in signals],
        "count": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/events/{signal_id}")
def get_event(signal_id: str, db: Session = Depends(get_db)) -> dict:
    signal = db.query(RiskSignal).filter(RiskSignal.id == signal_id).first()
    if not signal:
        raise HTTPException(status_code=404, detail="Event not found")

    result = _signal_to_dict(signal)

    # Add related events from same cluster
    if signal.event_cluster_id:
        related = (
            db.query(RiskSignal)
            .filter(
                RiskSignal.event_cluster_id == signal.event_cluster_id,
                RiskSignal.id != signal_id,
            )
            .order_by(desc(RiskSignal.created_at))
            .limit(10)
            .all()
        )
        result["related_events"] = [_signal_to_dict(r) for r in related]
    else:
        result["related_events"] = []

    # Add stress test results
    from app.models import StressSimulation
    stress_sims = (
        db.query(StressSimulation)
        .filter(StressSimulation.trigger_signal_id == signal_id)
        .all()
    )
    result["stress_results"] = [
        {
            "simulation_id": sim.id,
            "scenario": sim.scenario_name,
            "portfolio_before": sim.portfolio_before,
            "portfolio_after": sim.portfolio_after,
            "loss_percentage": sim.loss_percentage,
            "timestamp": sim.created_at.isoformat() if sim.created_at else "",
        }
        for sim in stress_sims
    ]

    return result
