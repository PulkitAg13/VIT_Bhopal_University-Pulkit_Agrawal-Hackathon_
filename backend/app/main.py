from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import analysis, demo, entities, events, health, ingestion, metrics, portfolio, stress, websocket
from app.core.config import get_settings
from app.core.logging import setup_logging

settings = get_settings()
logger = setup_logging(settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown."""
    # Startup
    log = logging.getLogger("finrisk.startup")
    log.info("FinRisk Intelligence starting up...")

    # Create database tables
    try:
        from app.core.database import engine, Base
        from app.models import (
            Source, Document, Entity, DocumentEntity,
            EventCluster, RiskSignal, Portfolio, PortfolioPosition,
            StressScenario, StressSimulation,
        )
        Base.metadata.create_all(bind=engine)
        log.info("Database tables created/verified")
    except Exception as exc:
        log.error("Database setup failed: %s", exc)

    # Seed portfolio
    try:
        from app.core.database import SessionLocal
        from app.services.portfolio.portfolio_service import PortfolioService
        db = SessionLocal()
        PortfolioService().seed_portfolio(db)
        db.close()
        log.info("Portfolio seeded")
    except Exception as exc:
        log.warning("Portfolio seeding skipped: %s", exc)

    # Pre-load models in background (non-blocking)
    try:
        from app.core.model_manager import get_model_manager
        mm = get_model_manager()
        # Load models (this can take time)
        mm.load_all()
    except Exception as exc:
        log.warning("Model pre-loading failed: %s — will load on first request", exc)

    log.info("FinRisk Intelligence ready")
    yield
    # Shutdown
    log.info("FinRisk Intelligence shutting down")


app = FastAPI(
    title="FinRisk Intelligence API",
    description="AI-powered financial risk intelligence and stress testing platform.",
    version="2.0.0",
    lifespan=lifespan,
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
    return {"service": "FinRisk Intelligence", "version": "2.0.0", "status": "ok"}
