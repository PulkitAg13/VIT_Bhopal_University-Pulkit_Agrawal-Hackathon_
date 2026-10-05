"""Stress testing endpoints — run, list, and view stress test results."""
from __future__ import annotations

from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.database import get_db
from app.api.dependencies import portfolio_service, stress_engine
from app.models import StressSimulation
from app.schemas import StressTestRequest, StressResultResponse, StressScenarioInfo

router = APIRouter(tags=["stress"])


@router.get("/stress-test/scenarios")
def list_stress_scenarios() -> Dict[str, List[Dict[str, Any]]]:
    scenarios = stress_engine.get_scenarios()
    return {"scenarios": scenarios}


@router.post("/stress-test", response_model=StressResultResponse)
@router.post("/stress-test/run", response_model=StressResultResponse)
def run_stress_test(payload: StressTestRequest, db: Session = Depends(get_db)) -> StressResultResponse:
    portfolio = portfolio_service.load_portfolio(db)
    try:
        result = stress_engine.stress_test(
            portfolio=portfolio,
            scenario_name=payload.scenario,
            db=db,
        )
        return StressResultResponse(**result)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/stress-test/results")
def list_stress_results(
    limit: int = 20,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    sims = (
        db.query(StressSimulation)
        .order_by(desc(StressSimulation.created_at))
        .limit(limit)
        .all()
    )
    return {
        "results": [
            {
                "simulation_id": sim.id,
                "scenario": sim.scenario_name,
                "portfolio_before": sim.portfolio_before,
                "portfolio_after": sim.portfolio_after,
                "absolute_loss": sim.absolute_loss,
                "loss_percentage": sim.loss_percentage,
                "is_auto_triggered": sim.is_auto_triggered,
                "trigger_signal_id": sim.trigger_signal_id,
                "timestamp": sim.created_at.isoformat() if sim.created_at else "",
            }
            for sim in sims
        ],
        "count": len(sims),
    }


@router.get("/stress-test/{simulation_id}", response_model=StressResultResponse)
def get_stress_result(simulation_id: str, db: Session = Depends(get_db)) -> StressResultResponse:
    sim = db.query(StressSimulation).filter(StressSimulation.id == simulation_id).first()
    if not sim:
        raise HTTPException(status_code=404, detail="Stress simulation not found")
    return StressResultResponse(
        simulation_id=sim.id,
        scenario=sim.scenario_name,
        description=stress_engine.scenarios.get(sim.scenario_name, {}).get("description", ""),
        assumptions=stress_engine.scenarios.get(sim.scenario_name, {}).get("assumptions", ""),
        portfolio_before=sim.portfolio_before,
        portfolio_after=sim.portfolio_after,
        absolute_loss=sim.absolute_loss,
        loss_percentage=sim.loss_percentage,
        asset_level_impacts=sim.asset_level_impacts or [],
        is_auto_triggered=sim.is_auto_triggered,
        trigger_signal_id=sim.trigger_signal_id,
        timestamp=sim.created_at.isoformat() if sim.created_at else "",
    )
