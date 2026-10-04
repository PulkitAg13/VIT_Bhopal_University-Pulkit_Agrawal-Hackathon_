from __future__ import annotations

from fastapi import APIRouter

from app.api.dependencies import risk_service

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    database_status = "ready" if risk_service.history else "warmup"
    return {
        "status": "ok",
        "service": "FinRisk Intelligence",
        "database": database_status,
        "redis": "ready",
        "model_status": "risk-engine-active",
    }
