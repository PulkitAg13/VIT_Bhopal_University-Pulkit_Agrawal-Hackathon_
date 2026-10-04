"""Entities endpoints — database-backed entity listing and detail."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.core.database import get_db
from app.models import Entity, DocumentEntity, RiskSignal, Document

router = APIRouter(tags=["entities"])


@router.get("/entities")
def list_entities(
    search: str | None = Query(default=None),
    entity_type: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> dict:
    query = db.query(Entity)
    if search:
        query = query.filter(
            Entity.canonical_name.ilike(f"%{search}%") | Entity.ticker.ilike(f"%{search}%")
        )
    if entity_type:
        query = query.filter(Entity.entity_type == entity_type)

    entities = query.all()
    items = []

    for entity in entities:
        # Get event count and averages
        doc_entities = db.query(DocumentEntity).filter(DocumentEntity.entity_id == entity.id).all()
        doc_ids = [de.document_id for de in doc_entities]

        if doc_ids:
            signals = (
                db.query(RiskSignal)
                .filter(RiskSignal.document_id.in_(doc_ids))
                .all()
            )
            event_count = len(signals)
            avg_risk = sum(s.impact_score for s in signals) / max(1, event_count)
            avg_sentiment = sum(s.sentiment_score for s in signals) / max(1, event_count)
            last_seen = max((s.created_at for s in signals), default=None)
        else:
            event_count = 0
            avg_risk = 0.0
            avg_sentiment = 0.0
            last_seen = None

        items.append({
            "id": entity.id,
            "canonical_name": entity.canonical_name,
            "ticker": entity.ticker,
            "entity_type": entity.entity_type,
            "event_count": event_count,
            "avg_risk": round(avg_risk, 2),
            "avg_sentiment": round(avg_sentiment, 4),
            "last_seen": last_seen.isoformat() if last_seen else None,
        })

    # Sort by event count descending
    items.sort(key=lambda x: x["event_count"], reverse=True)

    return {"items": items, "count": len(items)}


@router.get("/entities/{entity_id}")
def get_entity(entity_id: str, db: Session = Depends(get_db)) -> dict:
    # Find entity by ID, name, or ticker
    entity = db.query(Entity).filter(Entity.id == entity_id).first()
    if not entity:
        entity = db.query(Entity).filter(Entity.canonical_name == entity_id).first()
    if not entity:
        entity = db.query(Entity).filter(Entity.ticker == entity_id).first()
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    # Get related documents and signals
    doc_entities = db.query(DocumentEntity).filter(DocumentEntity.entity_id == entity.id).all()
    doc_ids = [de.document_id for de in doc_entities]

    events = []
    risk_timeline = []
    sentiment_timeline = []

    if doc_ids:
        signals = (
            db.query(RiskSignal)
            .filter(RiskSignal.document_id.in_(doc_ids))
            .order_by(desc(RiskSignal.created_at))
            .all()
        )

        for signal in signals:
            doc = signal.document
            events.append({
                "signal_id": signal.id,
                "text": doc.original_text if doc else "",
                "event_class": signal.event_class,
                "impact_score": signal.impact_score,
                "risk_level": signal.risk_level,
                "sentiment_label": signal.sentiment_label,
                "sentiment_score": signal.sentiment_score,
                "timestamp": signal.created_at.isoformat() if signal.created_at else "",
            })
            risk_timeline.append({
                "timestamp": signal.created_at.isoformat() if signal.created_at else "",
                "risk": signal.impact_score,
                "event_class": signal.event_class,
            })
            sentiment_timeline.append({
                "timestamp": signal.created_at.isoformat() if signal.created_at else "",
                "sentiment": signal.sentiment_score,
                "label": signal.sentiment_label,
            })

    avg_risk = sum(e["impact_score"] for e in events) / max(1, len(events))
    avg_sentiment = sum(e["sentiment_score"] for e in events) / max(1, len(events))

    return {
        "entity": {
            "id": entity.id,
            "canonical_name": entity.canonical_name,
            "ticker": entity.ticker,
            "entity_type": entity.entity_type,
            "event_count": len(events),
            "avg_risk": round(avg_risk, 2),
            "avg_sentiment": round(avg_sentiment, 4),
            "last_seen": events[0]["timestamp"] if events else None,
        },
        "events": events,
        "risk_timeline": risk_timeline,
        "sentiment_timeline": sentiment_timeline,
    }
