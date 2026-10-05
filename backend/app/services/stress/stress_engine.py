"""
Stress Testing Engine — Applies economically meaningful shocks
to portfolio positions based on scenario parameters.

CRITICAL FIX: The previous implementation ignored positive shock parameters
(commodity price increases, spread widening, default rates). This version
correctly applies ALL shocks regardless of sign.
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
        with open(_CONFIG_PATH, "r", encoding="utf-8") as fh:
            cfg = yaml.safe_load(fh)
        return cfg.get("scenarios", {})
    return {}


# Default scenarios with complete shock parameters
DEFAULT_SCENARIOS: Dict[str, Dict[str, Any]] = {
    "GEOPOLITICAL_SHOCK": {
        "description": "Geopolitical conflict disrupting trade and energy supply",
        "equity_shock": -0.10,
        "credit_spread_shock": 0.03,
        "interest_rate_shock": 0.02,
        "commodity_shock": 0.15,
        "liquidity_haircut": 0.05,
        "default_rate_increase": 0.02,
        "assumptions": "Equity decline from risk-off; commodity price surge from supply disruption; spread widening from uncertainty; modest rate impact",
    },
    "MACRO_RATE_SHOCK": {
        "description": "Aggressive monetary tightening with rate increases",
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
        "description": "Systemic credit event with defaults and spread blowout",
        "equity_shock": -0.15,
        "corporate_bond_shock": -0.12,
        "credit_spread_shock": 0.06,
        "default_rate_increase": 0.05,
        "liquidity_haircut": 0.10,
        "interest_rate_shock": -0.01,
        "commodity_shock": -0.08,
        "assumptions": "Flight to quality; corporate defaults rise; spreads widen dramatically; rates may fall as central banks intervene",
    },
    "LIQUIDITY_SHOCK": {
        "description": "Market liquidity freeze with forced selling",
        "equity_shock": -0.08,
        "corporate_bond_shock": -0.10,
        "credit_spread_shock": 0.04,
        "liquidity_haircut": 0.15,
        "derivative_haircut": 0.08,
        "default_rate_increase": 0.03,
        "interest_rate_shock": 0.01,
        "assumptions": "Liquidity premium rises; forced selling across assets; derivatives face margin calls",
    },
    "COMMODITY_SHOCK": {
        "description": "Major commodity price spike from supply disruption",
        "equity_shock": -0.04,
        "commodity_shock": 0.25,
        "interest_rate_shock": 0.01,
        "credit_spread_shock": 0.02,
        "liquidity_haircut": 0.03,
        "default_rate_increase": 0.015,
        "assumptions": "Energy/commodity surge raises input costs; modest equity decline; inflation concerns push rates",
    },
}


class StressEngine:
    """Portfolio stress testing engine with proper shock application."""

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
                "parameters": {k: v for k, v in params.items()
                              if k not in ("description", "assumptions")},
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
        """
        Run stress test on portfolio.

        CRITICAL: Correctly applies ALL shocks including positive ones
        (commodity price increases, spread widening, default rate increases).
        """
        cfg = self.scenarios.get(scenario_name, self.scenarios.get("GEOPOLITICAL_SHOCK", {}))
        before_total = float(portfolio.get("total_value", 100_000_000))
        after_total = 0.0
        asset_impacts: List[Dict[str, Any]] = []

        for position in portfolio.get("positions", []):
            value = float(position.get("notional", position.get("value", 0)))
            asset_class = position.get("asset_class", "Unknown")
            issuer = position.get("issuer", "")
            ticker = position.get("ticker", "")

            # Calculate shock for this position based on asset class and characteristics
            shock = self._compute_position_shock(asset_class, cfg, position)

            # Apply shock: negative shock = loss, positive shock on commodity = gain for commodity holders
            # but positive spread shock = loss for bond holders
            impacted_value = value * (1.0 + shock)
            impact_amount = impacted_value - value

            asset_impacts.append({
                "asset_id": position.get("asset_id", ""),
                "asset_class": asset_class,
                "issuer": issuer,
                "ticker": ticker,
                "duration": position.get("duration"),
                "before_value": round(value, 2),
                "after_value": round(impacted_value, 2),
                "impact": round(impact_amount, 2),
                "impact_pct": round(shock * 100, 2),
            })
            after_total += impacted_value

        abs_loss = before_total - after_total
        loss_pct = (abs_loss / before_total) * 100.0 if before_total > 0 else 0.0

        sim_id = str(uuid.uuid4())

        result = {
            "simulation_id": sim_id,
            "scenario": scenario_name,
            "description": cfg.get("description", ""),
            "assumptions": cfg.get("assumptions", ""),
            "trigger_signal_id": trigger_signal_id,
            "is_auto_triggered": is_auto_triggered,
            "portfolio_before": round(before_total, 2),
            "portfolio_after": round(after_total, 2),
            "absolute_loss": round(abs_loss, 2),
            "loss_percentage": round(loss_pct, 2),
            "asset_level_impacts": asset_impacts,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Persist to database
        if db is not None:
            sim = StressSimulation(
                id=sim_id,
                trigger_signal_id=trigger_signal_id,
                scenario_name=scenario_name,
                portfolio_id=portfolio.get("portfolio_id"),
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
        Compute the net shock for a position based on asset class, actual duration, and scenario.

        Returns a decimal shock (e.g., -0.10 for -10% loss, +0.05 for +5% gain).
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
            # Corporate bonds: direct shock + spread impact using actual position duration
            effective_duration = float(pos_duration) if pos_duration is not None and pos_duration > 0 else 4.0
            spread_impact = -credit_spread_shock * effective_duration
            direct = corporate_bond_shock if corporate_bond_shock else 0.0
            return direct + spread_impact - liquidity_haircut * 0.5

        elif "government bond" in ac:
            # Government bonds: rate impact on price using actual position duration
            # Price change ≈ -duration * rate change
            effective_duration = float(pos_duration) if pos_duration is not None and pos_duration > 0 else 5.0
            rate_impact = -interest_rate_shock * effective_duration
            direct = bond_price_shock if bond_price_shock else 0.0
            return direct + rate_impact

        elif "corporate loan" in ac or "loan" in ac:
            # Loans: default rate increase = expected loss increase
            return -default_rate_increase - liquidity_haircut * 0.2

        elif "derivative" in ac:
            # Derivatives: direct haircut + equity correlation + liquidity
            return -derivative_haircut + equity_shock * 0.5 - liquidity_haircut * 0.3

        elif "commodit" in ac:
            # Commodities: direct commodity price shock (can be positive!)
            return commodity_shock

        elif "cash" in ac:
            return 0.0

        else:
            # Unknown asset: apply average of equity and liquidity shock
            return equity_shock * 0.5 - liquidity_haircut * 0.2
