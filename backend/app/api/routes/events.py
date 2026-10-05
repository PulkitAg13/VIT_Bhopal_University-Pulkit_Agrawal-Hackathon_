"""Events endpoints — database-backed event listing and detail with accurate stress representation."""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.database import get_db
from app.models import RiskSignal, Document, DocumentEntity, Entity, StressSimulation
from app.schemas import EventListResponse

router = APIRouter(tags=["events"])


def _signal_to_dict(signal: RiskSignal, db: Optional[Session] = None) -> Dict[str, Any]:
    """Convert a RiskSignal ORM object to an API response dict.

    CRITICAL: stress_test.triggered is determined from the actual persisted
    StressSimulation, NOT just (impact_score >= 7).
    """
    doc = signal.document
    entities = []
    if doc and doc.document_entities:
        for de in doc.document_entities:
            ent = de.entity
            if ent:
                entities.append({
                    "canonical_name": ent.canonical_name,
                    "ticker": ent.ticker,
                    "type": ent.entity_type,
                    "confidence": de.confidence,
                })

    # Find actual persisted stress simulation triggered by this signal
    sim = None
    if signal.stress_simulations:
        sim = signal.stress_simulations[0]
    elif db is not None:
        sim = (
            db.query(StressSimulation)
            .filter(StressSimulation.trigger_signal_id == signal.id)
            .first()
        )

    if sim:
        stress_info = {
            "triggered": True,
            "scenario": sim.scenario_name,
            "simulation_id": sim.id,
            "is_auto_triggered": sim.is_auto_triggered,
            "result": {
                "simulation_id": sim.id,
                "scenario": sim.scenario_name,
                "portfolio_before": sim.portfolio_before,
                "portfolio_after": sim.portfolio_after,
                "absolute_loss": sim.absolute_loss,
                "loss_percentage": sim.loss_percentage,
                "asset_level_impacts": sim.asset_level_impacts or [],
                "timestamp": sim.created_at.isoformat() if sim.created_at else "",
            },
        }
    else:
        stress_info = {
            "triggered": False,
            "scenario": None,
            "simulation_id": None,
            "is_auto_triggered": False,
            "result": None,
        }

    return {
        "id": signal.id,
        "signal_id": signal.id,
        "document_id": signal.document_id,
        "timestamp": signal.created_at.isoformat() if signal.created_at else "",
        "created_at": signal.created_at.isoformat() if signal.created_at else "",
        "source": {
            "type": signal.source_type or "",
            "name": signal.source_name or "",
            "url": doc.source_url if doc else None,
        },
        "source_name": signal.source_name or "",
        "source_type": signal.source_type or "",
        "text": doc.original_text if doc else "",
        "entities": entities,
        "sentiment": {
            "label": signal.sentiment_label,
            "score": signal.sentiment_score,
            "confidence": signal.sentiment_confidence,
            "probabilities": signal.sentiment_probabilities or {},
        },
        "sentiment_label": signal.sentiment_label,
        "sentiment_score": signal.sentiment_score,
        "event": {
            "class": signal.event_class,
            "confidence": signal.event_confidence,
        },
        "event_class": signal.event_class,
        "event_confidence": signal.event_confidence,
        "impact": {
            "score": signal.impact_score,
            "risk_level": signal.risk_level,
            "components": signal.impact_components or {},
            "explanation": signal.explanation[-1] if signal.explanation else "",
        },
        "impact_score": signal.impact_score,
        "risk_level": signal.risk_level,
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
        "stress_test": stress_info,
    }


@router.get("/events", response_model=EventListResponse)
def list_events(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    event_class: Optional[str] = Query(default=None),
    risk_level: Optional[str] = Query(default=None),
    source_type: Optional[str] = Query(default=None),
    source: Optional[str] = Query(default=None),
    sentiment: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
) -> EventListResponse:
    query = db.query(RiskSignal).join(Document)

    if event_class:
        query = query.filter(RiskSignal.event_class == event_class)
    if risk_level:
        query = query.filter(RiskSignal.risk_level == risk_level)
    if source_type:
        query = query.filter(RiskSignal.source_type == source_type)
    if source:
        query = query.filter(
            (RiskSignal.source_name.ilike(f"%{source}%"))
            | (RiskSignal.source_type.ilike(f"%{source}%"))
        )
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

    items = [_signal_to_dict(s, db) for s in signals]
    return EventListResponse(
        items=items,
        count=total,
        page=page,
        page_size=page_size,
    )


@router.get("/events/{signal_id}")
def get_event(signal_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    signal = db.query(RiskSignal).filter(RiskSignal.id == signal_id).first()
    if not signal:
        raise HTTPException(status_code=404, detail="Event not found")

    result = _signal_to_dict(signal, db)

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
        result["related_events"] = [_signal_to_dict(r, db) for r in related]
    else:
        result["related_events"] = []

    return result
