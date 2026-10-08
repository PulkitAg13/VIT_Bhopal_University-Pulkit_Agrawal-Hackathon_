"""Health and readiness endpoints — query live service and model status."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.model_manager import get_model_manager, READY, LOADING, ERROR
from app.core.redis_client import redis_health
from app.schemas import HealthResponse, ReadinessResponse

router = APIRouter(tags=["health"])


import logging

logger = logging.getLogger("finrisk.health")


def _evaluate_system_health(db: Session) -> dict:
    # 1. Database check
    db_status = "connected"
    try:
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
    except Exception as exc:
        logger.error("Database health check error: %s", exc, exc_info=True)
        db_status = "error"

    # 2. Redis check
    redis_info = redis_health()
    raw_redis = redis_info.get("status", "unavailable")
    if raw_redis == "connected":
        redis_status = "connected"
    elif raw_redis == "unavailable":
        redis_status = "unavailable"
    else:
        logger.error("Redis health check reported error: %s", redis_info.get("info", raw_redis))
        redis_status = "error"

    # 3. Models check
    mm = get_model_manager()
    raw_model_status = mm.status()
    safe_models: dict[str, str] = {}
    for name, st in raw_model_status.items():
        if name == "device":
            safe_models[name] = str(st)
            continue
        if st == READY:
            safe_models[name] = "ready"
        elif st == LOADING:
            safe_models[name] = "loading"
        elif str(st).startswith(ERROR):
            logger.error("Model '%s' health check reported error: %s", name, st)
            safe_models[name] = "error"
        else:
            safe_models[name] = "not_loaded"

    model_values = [
        safe_models.get("finbert", "not_loaded"),
        safe_models.get("embedding_model", "not_loaded"),
        safe_models.get("event_classifier", "not_loaded"),
        safe_models.get("ner_model", "not_loaded"),
    ]

    # Evaluate overall health status: healthy, degraded, or unhealthy
    if db_status != "connected":
        overall_status = "unhealthy"
    elif any(s == "error" for s in model_values) or redis_status == "error":
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
        "database": db_status,
        "redis": redis_status,
        "models": safe_models,
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
