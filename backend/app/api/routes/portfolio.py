from __future__ import annotations

from fastapi import APIRouter

from app.services.portfolio.portfolio_service import PortfolioService

router = APIRouter(tags=["portfolio"])


@router.get("/portfolio")
def get_portfolio() -> dict:
    service = PortfolioService()
    return service.load_portfolio()
