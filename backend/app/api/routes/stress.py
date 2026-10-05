"""Stress testing endpoints — run, list, and view stress test results."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.database import get_db
from app.api.dependencies import portfolio_service, stress_engine
from app.models import StressSimulation
from app.schemas import StressTestRequest

router = APIRouter(tags=["stress"])


@router.get("/stress-test/scenarios")
def list_stress_scenarios() -> dict:
    scenarios = stress_engine.get_scenarios()
    return {"scenarios": scenarios}


@router.post("/stress-test")
@router.post("/stress-test/run")
def run_stress_test(payload: StressTestRequest, db: Session = Depends(get_db)) -> dict:
    portfolio = portfolio_service.load_portfolio(db)
    result = stress_engine.stress_test(
        portfolio=portfolio,
        scenario_name=payload.scenario,
        db=db,
    )
    return result


@router.get("/stress-test/results")
def list_stress_results(
    limit: int = 20,
    db: Session = Depends(get_db),
) -> dict:
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


@router.get("/stress-test/{simulation_id}")
def get_stress_result(simulation_id: str, db: Session = Depends(get_db)) -> dict:
    sim = db.query(StressSimulation).filter(StressSimulation.id == simulation_id).first()
    if not sim:
        raise HTTPException(status_code=404, detail="Stress simulation not found")
    return {
        "simulation_id": sim.id,
        "scenario": sim.scenario_name,
        "portfolio_before": sim.portfolio_before,
        "portfolio_after": sim.portfolio_after,
        "absolute_loss": sim.absolute_loss,
        "loss_percentage": sim.loss_percentage,
        "asset_level_impacts": sim.asset_level_impacts or [],
        "is_auto_triggered": sim.is_auto_triggered,
        "trigger_signal_id": sim.trigger_signal_id,
        "timestamp": sim.created_at.isoformat() if sim.created_at else "",
    }
