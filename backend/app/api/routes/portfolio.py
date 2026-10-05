"""Portfolio endpoints — database-backed portfolio and exposure data."""
from __future__ import annotations

from typing import Any, Dict
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.dependencies import portfolio_service
from app.schemas import PortfolioResponse

router = APIRouter(tags=["portfolio"])


@router.get("/portfolio", response_model=PortfolioResponse)
def get_portfolio(db: Session = Depends(get_db)) -> PortfolioResponse:
    portfolio = portfolio_service.load_portfolio(db)
    # Ensure breakdown is populated
    exposure_breakdown = portfolio_service.get_exposure(db)
    portfolio["by_asset_class"] = exposure_breakdown.get("by_asset_class", [])
    portfolio["by_sector"] = exposure_breakdown.get("by_sector", [])
    return PortfolioResponse(**portfolio)


@router.get("/portfolio/exposure")
def get_portfolio_exposure(db: Session = Depends(get_db)) -> Dict[str, Any]:
    return portfolio_service.get_exposure(db)
