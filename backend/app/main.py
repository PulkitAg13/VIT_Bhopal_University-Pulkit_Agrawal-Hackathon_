from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import (
    analysis, demo, entities, events, health,
    ingestion, metrics, portfolio, stress, websocket,
)
from app.api.routes.websocket import manager, start_redis_subscriber_task
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.core.model_manager import ModelUnavailableError, get_model_manager

settings = get_settings()
logger = setup_logging(settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown."""
    log = logging.getLogger("finrisk.startup")
    log.info("FinRisk Intelligence starting up...")

    # Seed initial portfolio data if table exists (schema is created via Alembic)
    try:
        from app.core.database import SessionLocal
        from app.services.portfolio.portfolio_service import PortfolioService
        db = SessionLocal()
        PortfolioService().seed_portfolio(db)
        db.close()
        log.info("Portfolio verified/seeded")
    except Exception as exc:
        log.warning("Portfolio seeding skipped: %s", exc)

    # Start single Redis subscriber task for all WebSocket connections
    subscriber_task = asyncio.create_task(start_redis_subscriber_task(manager))
    log.info("Single Redis subscriber task started")

    # Pre-load models asynchronously in background thread safely
    try:
        mm = get_model_manager()
        asyncio.create_task(asyncio.to_thread(mm.load_all))
        log.info("Model pre-loading scheduled in background thread")
    except Exception as exc:
        log.warning("Model background scheduling failed: %s", exc)

    log.info("FinRisk Intelligence ready")
    yield

    # Shutdown
    log.info("FinRisk Intelligence shutting down...")
    subscriber_task.cancel()
    try:
        await subscriber_task
    except asyncio.CancelledError:
        pass
    log.info("FinRisk Intelligence shutdown complete")


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


@app.exception_handler(ModelUnavailableError)
async def model_unavailable_handler(request: Request, exc: ModelUnavailableError) -> JSONResponse:
    """Return controlled HTTP 503 when required NLP model is unavailable."""
    logger.warning("ModelUnavailableError on %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=503,
        content=exc.to_dict(),
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    """Return controlled HTTP 400 for invalid inputs or unknown scenarios."""
    logger.warning("ValueError on %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=400,
        content={
            "error_code": "INVALID_REQUEST",
            "message": str(exc),
            "retryable": False,
        },
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
