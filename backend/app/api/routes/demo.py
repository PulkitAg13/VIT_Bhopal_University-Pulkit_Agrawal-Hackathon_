"""Demo endpoint — runs the full pipeline with a deterministic scenario."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.dependencies import risk_service, portfolio_service, stress_engine

logger = logging.getLogger("finrisk.demo")

router = APIRouter(tags=["demo"])

DEMO_TEXT = (
    "Escalating geopolitical tensions disrupt critical energy supply routes, "
    "raising concerns over global inflation and corporate input costs."
)


@router.post("/demo/run")
def run_demo(db: Session = Depends(get_db)) -> dict:
    """Run the full pipeline demo: Ingest → Analyze → Risk → Stress Test → Portfolio Impact."""
    steps = []

    # Step 1: Ingest
    steps.append({
        "step": 1,
        "name": "Ingest",
        "status": "complete",
        "detail": "Synthetic demo event ingested",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    # Step 2: Analyze (runs full NLP pipeline)
    try:
        result = risk_service.analyze(
            text=DEMO_TEXT,
            source_name="Synthetic Demo Dataset",
            source_type="demo",
            db=db,
        )
        steps.append({
            "step": 2,
            "name": "Analyze",
            "status": "complete",
            "detail": f"Sentiment: {result['sentiment']['label']} ({result['sentiment']['score']:+.2f}), "
                      f"Event: {result['event']['class']} ({result['event']['confidence']:.2f})",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
    except Exception as exc:
        logger.error("Demo analysis failed: %s", exc)
        steps.append({"step": 2, "name": "Analyze", "status": "error", "detail": str(exc)})
        return {"steps": steps, "demo_event": {}, "stress_test": None, "success": False}

    # Step 3: Risk detected
    steps.append({
        "step": 3,
        "name": "Risk Detected",
        "status": "complete",
        "detail": f"Impact: {result['impact']['score']}/10 ({result['impact']['risk_level']}), "
                  f"Trajectory: {result['risk_trajectory']}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    # Step 4: Stress test (if triggered)
    stress_result = result.get("stress_test", {}).get("result")
    if result.get("stress_test", {}).get("triggered"):
        scenario = result["stress_test"].get("scenario", "GEOPOLITICAL_SHOCK")
        if not stress_result:
            try:
                portfolio = portfolio_service.load_portfolio(db)
                stress_result = stress_engine.stress_test(
                    portfolio=portfolio,
                    scenario_name=scenario,
                    trigger_signal_id=result.get("signal_id"),
                    is_auto_triggered=True,
                    db=db,
                )
            except Exception as exc:
                logger.error("Demo stress test failed: %s", exc)
                steps.append({"step": 4, "name": "Stress Test", "status": "error", "detail": str(exc)})
                return {"steps": steps, "demo_event": result, "stress_test": None, "success": False}

        steps.append({
            "step": 4,
            "name": "Stress Test (Auto-Triggered)",
            "status": "complete",
            "detail": f"Scenario: {scenario}, Simulated Loss: ${stress_result['absolute_loss']:,.0f} "
                      f"({stress_result['loss_percentage']:.1f}%)",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
    else:
        steps.append({
            "step": 4,
            "name": "Stress Test",
            "status": "skipped",
            "detail": f"Impact {result['impact']['score']:.1f} below trigger threshold",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    # Step 5: Portfolio impact
    steps.append({
        "step": 5,
        "name": "Portfolio Impact",
        "status": "complete",
        "detail": f"Portfolio: ${stress_result['portfolio_after']:,.0f}" if stress_result
                  else "No stress test triggered",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    return {
        "steps": steps,
        "demo_event": result,
        "stress_test": stress_result,
        "success": True,
    }
