from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import analysis, demo, entities, events, health, ingestion, metrics, portfolio, stress, websocket
from app.core.config import get_settings
from app.core.logging import setup_logging

settings = get_settings()
logger = setup_logging(settings.log_level)

app = FastAPI(
    title="FinRisk Intelligence API",
    description="AI-powered financial risk intelligence and stress testing platform.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api/v1")
app.include_router(analysis.router, prefix="/api/v1")
app.include_router(ingestion.router, prefix="/api/v1")
app.include_router(events.router, prefix="/api/v1")
app.include_router(entities.router, prefix="/api/v1")
app.include_router(portfolio.router, prefix="/api/v1")
app.include_router(stress.router, prefix="/api/v1")
app.include_router(metrics.router, prefix="/api/v1")
app.include_router(demo.router, prefix="/api/v1")
app.include_router(websocket.router)


@app.get("/")
def root() -> dict:
    return {"service": "FinRisk Intelligence", "status": "ok"}
