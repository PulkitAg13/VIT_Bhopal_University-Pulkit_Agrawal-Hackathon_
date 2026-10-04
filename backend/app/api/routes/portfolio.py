from __future__ import annotations

from fastapi import APIRouter

from app.services.portfolio.portfolio_service import PortfolioService

router = APIRouter(tags=["portfolio"])


@router.get("/portfolio")
def get_portfolio() -> dict:
    service = PortfolioService()
    return service.load_portfolio()


@router.get("/portfolio/exposure")
def get_portfolio_exposure() -> dict:
    portfolio = get_portfolio()
    positions = portfolio.get("positions", [])
    total = float(portfolio.get("total_value", 0.0) or 0.0)
    exposures = []
    for position in positions:
        value = float(position.get("value", 0.0) or 0.0)
        exposures.append({
            "asset_class": position.get("asset_class", "Unknown"),
            "value": value,
            "weight": round((value / total) * 100.0, 2) if total else 0.0,
            "exposure": position.get("exposure", 0.0),
        })
    return {"portfolio_id": portfolio.get("portfolio_id", "default"), "total_value": total, "positions": exposures}
