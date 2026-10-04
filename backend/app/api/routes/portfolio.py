"""Portfolio endpoints — database-backed portfolio and exposure data."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.dependencies import portfolio_service

router = APIRouter(tags=["portfolio"])


@router.get("/portfolio")
def get_portfolio(db: Session = Depends(get_db)) -> dict:
    return portfolio_service.load_portfolio(db)


@router.get("/portfolio/exposure")
def get_portfolio_exposure(db: Session = Depends(get_db)) -> dict:
    return portfolio_service.get_exposure(db)
