"""Health and readiness endpoints — query live service and model status."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.model_manager import get_model_manager, READY, LOADING, ERROR
from app.core.redis_client import redis_health
from app.schemas import HealthResponse, ReadinessResponse

router = APIRouter(tags=["health"])


def _evaluate_system_health(db: Session) -> dict:
    # 1. Database check
    db_status = "connected"
    try:
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
    except Exception as exc:
        db_status = f"error: {exc}"

    # 2. Redis check
    redis_info = redis_health()
    redis_status = redis_info.get("status", "unavailable")

    # 3. Models check
    mm = get_model_manager()
    model_status = mm.status()
    model_values = [
        model_status["finbert"],
        model_status["embedding_model"],
        model_status["event_classifier"],
        model_status["ner_model"],
    ]

    # Evaluate overall health status: healthy, degraded, or unhealthy
    if db_status != "connected":
        overall_status = "unhealthy"
    elif any(s.startswith(ERROR) for s in model_values):
        overall_status = "degraded"
    elif any(s == LOADING for s in model_values) or redis_status != "connected":
        overall_status = "degraded"
    elif all(s == READY for s in model_values):
        overall_status = "healthy"
    else:
        # Not loaded yet
        overall_status = "degraded"

    return {
        "status": overall_status,
        "service": "FinRisk Intelligence",
        "database": "connected" if db_status == "connected" else "error",
        "redis": redis_status,
        "models": {
            "finbert": model_status["finbert"],
            "embedding_model": model_status["embedding_model"],
            "event_classifier": model_status["event_classifier"],
            "ner_model": model_status["ner_model"],
        },
    }


@router.get("/health", response_model=HealthResponse)
def health(db: Session = Depends(get_db)) -> HealthResponse:
    """Live health status check distinguishing healthy, degraded, and unhealthy."""
    info = _evaluate_system_health(db)
    return HealthResponse(**info)


@router.get("/readiness", response_model=ReadinessResponse)
def readiness(db: Session = Depends(get_db)) -> ReadinessResponse:
    """Model and dependency readiness probe for orchestration and startup."""
    info = _evaluate_system_health(db)
    mm = get_model_manager()
    readiness_state = mm.get_readiness()["readiness"]

    if info["database"] != "connected":
        status = "not_ready"
    elif readiness_state == "ready" and info["redis"] == "connected":
        status = "ready"
    elif readiness_state in ("ready", "degraded"):
        status = "degraded"
    else:
        status = "not_ready"

    return ReadinessResponse(
        status=status,
        database=info["database"],
        redis=info["redis"],
        models=info["models"],
    )
