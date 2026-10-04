from __future__ import annotations

from fastapi import APIRouter

from app.api.dependencies import risk_service

router = APIRouter(tags=["metrics"])


@router.get("/metrics")
def metrics() -> dict:
    events = risk_service.history
    avg_impact = sum(item["impact"]["score"] for item in events) / max(1, len(events)) if events else 0
    avg_sentiment = sum(item["sentiment"]["score"] for item in events) / max(1, len(events)) if events else 0
    return {
        "events_processed": len(events),
        "critical_events": sum(1 for item in events if item["impact"]["risk_level"] == "CRITICAL"),
        "high_risk_events": sum(1 for item in events if item["impact"]["risk_level"] == "HIGH"),
        "average_sentiment": round(avg_sentiment, 4),
        "average_impact": round(avg_impact, 4),
        "portfolio_exposure": 0.7,
        "market_risk": "ELEVATED",
    }
