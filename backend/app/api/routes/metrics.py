"""Metrics and analytics endpoints — all data from database."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.core.database import get_db
from app.models import RiskSignal

router = APIRouter(tags=["metrics"])


def _compute_metrics(db: Session) -> dict:
    """Compute all metrics from database."""
    total = db.query(func.count(RiskSignal.id)).scalar() or 0

    if total == 0:
        return {
            "events_processed": 0,
            "high_risk_events": 0,
            "critical_events": 0,
            "average_sentiment": 0.0,
            "average_impact": 0.0,
            "overall_risk": 0.0,
            "market_risk": "LOW",
        }

    high_risk = db.query(func.count(RiskSignal.id)).filter(RiskSignal.risk_level == "HIGH").scalar() or 0
    critical = db.query(func.count(RiskSignal.id)).filter(RiskSignal.risk_level == "CRITICAL").scalar() or 0
    avg_sentiment = db.query(func.avg(RiskSignal.sentiment_score)).scalar() or 0.0
    avg_impact = db.query(func.avg(RiskSignal.impact_score)).scalar() or 0.0

    overall_risk = round(min(10.0, float(avg_impact) * 1.1 + 0.5), 2)
    market_risk = "ELEVATED" if overall_risk >= 6 else "MODERATE" if overall_risk >= 4 else "LOW"

    return {
        "events_processed": total,
        "high_risk_events": high_risk,
        "critical_events": critical,
        "average_sentiment": round(float(avg_sentiment), 4),
        "average_impact": round(float(avg_impact), 4),
        "overall_risk": overall_risk,
        "market_risk": market_risk,
    }


@router.get("/metrics")
def metrics(db: Session = Depends(get_db)) -> dict:
    return _compute_metrics(db)


@router.get("/risk/overview")
def risk_overview(db: Session = Depends(get_db)) -> dict:
    return _compute_metrics(db)


@router.get("/risk/timeline")
def risk_timeline(db: Session = Depends(get_db)) -> list:
    signals = (
        db.query(RiskSignal)
        .order_by(desc(RiskSignal.created_at))
        .limit(30)
        .all()
    )
    # Reverse to chronological order
    signals.reverse()
    return [
        {
            "timestamp": s.created_at.isoformat() if s.created_at else "",
            "risk": s.impact_score,
            "event_class": s.event_class,
            "sentiment": s.sentiment_score,
        }
        for s in signals
    ]


@router.get("/analytics/overview")
def analytics_overview(db: Session = Depends(get_db)) -> dict:
    base = _compute_metrics(db)
    signals = db.query(RiskSignal).all()

    # Distributions
    event_dist: dict = {}
    sentiment_dist: dict = {}
    risk_dist: dict = {}
    source_dist: dict = {}

    for s in signals:
        event_dist[s.event_class] = event_dist.get(s.event_class, 0) + 1
        sentiment_dist[s.sentiment_label] = sentiment_dist.get(s.sentiment_label, 0) + 1
        risk_dist[s.risk_level] = risk_dist.get(s.risk_level, 0) + 1
        src = s.source_type or "unknown"
        source_dist[src] = source_dist.get(src, 0) + 1

    return {
        **base,
        "event_distribution": event_dist,
        "sentiment_distribution": sentiment_dist,
        "risk_distribution": risk_dist,
        "source_distribution": source_dist,
    }
