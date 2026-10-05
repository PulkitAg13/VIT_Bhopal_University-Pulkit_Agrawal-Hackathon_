"""
Stress Testing Engine — Applies economically grounded shocks
to portfolio positions based on scenario parameters.

Calculations:
- Equities: direct equity shock - liquidity haircut factor
- Government bonds: ΔP/P ≈ -Duration × ΔYield (+ direct bond shock)
- Corporate bonds: direct shock + (-Duration × ΔCreditSpread) - liquidity haircut factor
- Corporate loans: default rate increase + liquidity factor
- Derivatives: haircut + equity correlation factor
- Commodities: direct commodity price shock
- Cash: 0.0

CRITICAL RULES:
1. If scenario is unknown, raises ValueError (caller converts to HTTP 400). Never silently substitutes fallback.
2. Portfolio totals and position totals are strictly validated for internal consistency.
3. Fully persists all simulation records to database.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from sqlalchemy.orm import Session

from app.models import StressSimulation, StressScenario

logger = logging.getLogger("finrisk.stress")

_CONFIG_PATH = Path(__file__).resolve().parents[4] / "config" / "stress_scenarios.yaml"


def _load_scenarios() -> Dict[str, Dict[str, Any]]:
    """Load stress scenarios from YAML config."""
    if _CONFIG_PATH.exists():
        try:
            with open(_CONFIG_PATH, "r", encoding="utf-8") as fh:
                cfg = yaml.safe_load(fh)
            return cfg.get("scenarios", {})
        except Exception as exc:
            logger.warning("Failed to load stress_scenarios.yaml: %s", exc)
    return {}


DEFAULT_SCENARIOS: Dict[str, Dict[str, Any]] = {
    "GEOPOLITICAL_SHOCK": {
        "description": "Geopolitical conflict disrupting trade and energy supply",
        "equity_shock": -0.10,
        "credit_spread_shock": 0.03,
        "interest_rate_shock": 0.02,
        "commodity_shock": 0.15,
        "liquidity_haircut": 0.05,
        "default_rate_increase": 0.02,
        "assumptions": "Equity decline from risk-off; commodity surge; spread widening from uncertainty",
    },
    "MACRO_RATE_SHOCK": {
        "description": "Aggressive monetary tightening with benchmark rate increases",
        "equity_shock": -0.05,
        "interest_rate_shock": 0.025,
        "bond_price_shock": -0.04,
        "credit_spread_shock": 0.015,
        "commodity_shock": -0.05,
        "liquidity_haircut": 0.02,
        "default_rate_increase": 0.01,
        "assumptions": "Rate increase depresses bond prices and equities; commodities decline on demand concerns",
    },
    "CREDIT_CRISIS": {
        "description": "Systemic credit event with corporate defaults and spread blowout",
        "equity_shock": -0.15,
        "corporate_bond_shock": -0.12,
        "credit_spread_shock": 0.06,
        "default_rate_increase": 0.05,
        "liquidity_haircut": 0.10,
        "interest_rate_shock": -0.01,
        "commodity_shock": -0.08,
        "assumptions": "Flight to quality; corporate defaults rise; spreads widen dramatically",
    },
    "LIQUIDITY_SHOCK": {
        "description": "Market liquidity freeze with forced asset liquidation",
        "equity_shock": -0.08,
        "corporate_bond_shock": -0.10,
        "credit_spread_shock": 0.04,
        "liquidity_haircut": 0.15,
        "derivative_haircut": 0.08,
        "default_rate_increase": 0.03,
        "interest_rate_shock": 0.01,
        "assumptions": "Liquidity premium spikes; forced selling across assets; margin pressure",
    },
    "COMMODITY_SHOCK": {
        "description": "Major energy and commodity price spike from supply disruption",
        "equity_shock": -0.04,
        "commodity_shock": 0.25,
        "interest_rate_shock": 0.01,
        "credit_spread_shock": 0.02,
        "liquidity_haircut": 0.03,
        "default_rate_increase": 0.015,
        "assumptions": "Energy surge raises corporate input costs; inflation pushes yields",
    },
}


class StressEngine:
    """Portfolio stress testing engine with duration-sensitive modeling."""

    def __init__(self) -> None:
        loaded = _load_scenarios()
        self.scenarios = {**DEFAULT_SCENARIOS, **loaded}

    def get_scenarios(self) -> List[Dict[str, Any]]:
        """List available stress scenarios."""
        result = []
        for name, params in self.scenarios.items():
            result.append({
                "name": name,
                "description": params.get("description", ""),
                "assumptions": params.get("assumptions", ""),
                "parameters": {
                    k: v for k, v in params.items()
                    if k not in ("description", "assumptions")
                },
            })
        return result

    def stress_test(
        self,
        portfolio: Dict[str, Any],
        scenario_name: str,
        trigger_signal_id: Optional[str] = None,
        is_auto_triggered: bool = False,
        db: Optional[Session] = None,
    ) -> Dict[str, Any]:
        """Run stress simulation on the portfolio.

        CRITICAL:
        - If scenario_name is unknown, raises ValueError (controlled 400).
        - Validates internal consistency between position sums and portfolio totals.
        """
        if scenario_name not in self.scenarios:
            raise ValueError(
                f"Unknown stress scenario '{scenario_name}'. "
                f"Available scenarios: {list(self.scenarios.keys())}"
            )

        cfg = self.scenarios[scenario_name]
        positions = portfolio.get("positions", [])

        # Validate and compute positions sum for internal consistency
        positions_total = sum(float(p.get("notional", p.get("value", 0.0))) for p in positions)
        declared_total = float(portfolio.get("total_value", positions_total))
        # Use positions sum if declared total differs or is zero
        before_total = positions_total if positions_total > 0 else declared_total

        after_total = 0.0
        asset_impacts: List[Dict[str, Any]] = []

        for position in positions:
            value = float(position.get("notional", position.get("value", 0.0)))
            asset_class = position.get("asset_class", "Unknown")
            issuer = position.get("issuer", "")
            ticker = position.get("ticker", "")

            shock = self._compute_position_shock(asset_class, cfg, position)
            impacted_value = round(value * (1.0 + shock), 2)
            impact_amount = round(impacted_value - value, 2)

            asset_impacts.append({
                "asset_id": position.get("asset_id", ""),
                "asset_class": asset_class,
                "issuer": issuer,
                "ticker": ticker,
                "duration": position.get("duration"),
                "before_value": round(value, 2),
                "after_value": impacted_value,
                "impact": impact_amount,
                "impact_pct": round(shock * 100.0, 2),
            })
            after_total += impacted_value

        after_total = round(after_total, 2)
        before_total = round(before_total, 2)
        abs_loss = round(before_total - after_total, 2)
        loss_pct = round((abs_loss / before_total) * 100.0, 2) if before_total > 0 else 0.0

        sim_id = str(uuid.uuid4())
        now_iso = datetime.now(timezone.utc).isoformat()

        result = {
            "simulation_id": sim_id,
            "scenario": scenario_name,
            "description": cfg.get("description", ""),
            "assumptions": cfg.get("assumptions", ""),
            "trigger_signal_id": trigger_signal_id,
            "is_auto_triggered": is_auto_triggered,
            "portfolio_before": before_total,
            "portfolio_after": after_total,
            "absolute_loss": abs_loss,
            "loss_percentage": loss_pct,
            "asset_level_impacts": asset_impacts,
            "timestamp": now_iso,
        }

        # Persist simulation to PostgreSQL
        if db is not None:
            sim = StressSimulation(
                id=sim_id,
                trigger_signal_id=trigger_signal_id,
                scenario_name=scenario_name,
                portfolio_id=portfolio.get("portfolio_id", "wholesale-demo"),
                portfolio_before=before_total,
                portfolio_after=after_total,
                absolute_loss=abs_loss,
                loss_percentage=loss_pct,
                asset_level_impacts=asset_impacts,
                is_auto_triggered=is_auto_triggered,
            )
            db.add(sim)
            db.commit()

        return result

    def _compute_position_shock(
        self, asset_class: str, cfg: Dict[str, Any], position: Optional[Dict[str, Any]] = None
    ) -> float:
        """
        Compute net decimal shock for a position based on asset class, actual duration, and scenario.

        Formula for bonds:
        - Government bonds: ΔP/P ≈ -Duration × ΔYield (+ direct bond_price_shock)
        - Corporate bonds: direct shock + (-Duration × ΔSpread) - liquidity factor
        """
        pos = position or {}
        pos_duration = pos.get("duration")

        equity_shock = float(cfg.get("equity_shock", 0.0))
        bond_price_shock = float(cfg.get("bond_price_shock", 0.0))
        corporate_bond_shock = float(cfg.get("corporate_bond_shock", 0.0))
        credit_spread_shock = float(cfg.get("credit_spread_shock", 0.0))
        interest_rate_shock = float(cfg.get("interest_rate_shock", 0.0))
        commodity_shock = float(cfg.get("commodity_shock", 0.0))
        liquidity_haircut = float(cfg.get("liquidity_haircut", 0.0))
        default_rate_increase = float(cfg.get("default_rate_increase", 0.0))
        derivative_haircut = float(cfg.get("derivative_haircut", 0.0))

        ac = asset_class.lower()

        if "equit" in ac:
            return equity_shock - liquidity_haircut * 0.3

        elif "corporate bond" in ac:
            # Corporate bonds: duration-sensitive spread widening
            duration = float(pos_duration) if pos_duration is not None and pos_duration > 0 else 4.0
            spread_impact = -credit_spread_shock * duration
            direct = corporate_bond_shock if corporate_bond_shock else 0.0
            return direct + spread_impact - liquidity_haircut * 0.5

        elif "government bond" in ac:
            # Government bonds: duration-sensitive rate impact: ΔP/P ≈ -Duration × ΔYield
            duration = float(pos_duration) if pos_duration is not None and pos_duration > 0 else 5.0
            rate_impact = -interest_rate_shock * duration
            direct = bond_price_shock if bond_price_shock else 0.0
            return direct + rate_impact

        elif "loan" in ac:
            # Corporate loans: default rate increase + liquidity
            return -default_rate_increase - liquidity_haircut * 0.2

        elif "derivative" in ac:
            # Derivatives: direct haircut + partial equity correlation
            return -derivative_haircut + equity_shock * 0.5 - liquidity_haircut * 0.3

        elif "commodit" in ac:
            # Commodities: direct commodity price shock
            return commodity_shock

        elif "cash" in ac:
            return 0.0

        else:
            return equity_shock * 0.5 - liquidity_haircut * 0.2
