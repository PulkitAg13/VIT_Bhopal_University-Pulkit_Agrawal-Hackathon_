"""Health check endpoint — queries actual service status."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.model_manager import get_model_manager
from app.core.redis_client import redis_health

router = APIRouter(tags=["health"])


@router.get("/health")
def health(db: Session = Depends(get_db)) -> dict:
    # Check database
    db_status = "connected"
    try:
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"

    # Check Redis
    redis_info = redis_health()

    # Check models
    mm = get_model_manager()
    model_status = mm.status()

    return {
        "status": "ok",
        "service": "FinRisk Intelligence",
        "database": db_status,
        "redis": redis_info.get("status", "unavailable"),
        "models": model_status,
    }
