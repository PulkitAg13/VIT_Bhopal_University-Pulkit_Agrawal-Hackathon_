from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.portfolio.portfolio_service import PortfolioService
from app.services.stress.stress_engine import StressEngine

router = APIRouter(tags=["stress"])


class StressRequest(BaseModel):
    scenario: str = "GEOPOLITICAL_SHOCK"


@router.get("/stress-test/scenarios")
def list_stress_scenarios() -> dict:
    return {"scenarios": ["GEOPOLITICAL_SHOCK", "MACRO_RATE_SHOCK", "CREDIT_CRISIS", "LIQUIDITY_SHOCK"]}


@router.get("/stress-test")
def list_scenarios() -> dict:
    return list_stress_scenarios()


@router.get("/stress-test/{scenario_name}")
def get_stress_scenario(scenario_name: str) -> dict:
    service = PortfolioService()
    portfolio = service.load_portfolio()
    engine = StressEngine()
    return engine.stress_test(portfolio, scenario_name)


@router.post("/stress-test")
def run_stress_test(payload: StressRequest) -> dict:
    service = PortfolioService()
    portfolio = service.load_portfolio()
    engine = StressEngine()
    return engine.stress_test(portfolio, payload.scenario)
