from __future__ import annotations

from fastapi import APIRouter

from app.api.dependencies import risk_service
from app.services.portfolio.portfolio_service import PortfolioService
from app.services.stress.stress_engine import StressEngine

router = APIRouter(tags=["demo"])


@router.post("/demo/run")
def run_demo() -> dict:
    sample_text = (
        "Escalating geopolitical tensions disrupt critical energy supply routes, raising concerns over global inflation and corporate input costs."
    )
    result = risk_service.analyze(sample_text, "Yahoo Finance RSS", "rss")
    portfolio = PortfolioService().load_portfolio()
    stress = StressEngine().stress_test(portfolio, result["stress_test"]["scenario"])
    return {"demo_event": result, "stress_test": stress}
