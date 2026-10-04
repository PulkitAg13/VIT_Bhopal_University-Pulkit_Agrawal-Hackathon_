from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "service": "FinRisk Intelligence",
        "database": "demo-mode",
        "redis": "demo-mode",
        "model_status": "heuristic-risk-engine",
    }
