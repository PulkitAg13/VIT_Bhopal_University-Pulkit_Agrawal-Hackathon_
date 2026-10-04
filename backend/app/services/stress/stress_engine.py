from __future__ import annotations

from typing import Any, Dict

from app.services.portfolio.portfolio_service import PortfolioService


class StressEngine:
    def __init__(self, scenario_config: Dict[str, Any] | None = None) -> None:
        self.portfolio_service = PortfolioService()
        self.scenario_config = scenario_config or {
            "GEOPOLITICAL_SHOCK": {"equity_shock": -0.10, "credit_spread_shock": 0.03, "interest_rate_shock": 0.02, "commodity_shock": 0.08},
            "MACRO_RATE_SHOCK": {"equity_shock": -0.05, "interest_rate_shock": 0.02, "bond_price_shock": -0.04},
            "CREDIT_CRISIS": {"corporate_bond_shock": -0.12, "loan_default_rate": 0.05, "equity_shock": -0.15},
            "LIQUIDITY_SHOCK": {"corporate_bond_shock": -0.10, "derivative_haircut": -0.05},
        }

    def stress_test(self, portfolio: Dict[str, Any], scenario_name: str) -> Dict[str, Any]:
        cfg = self.scenario_config.get(scenario_name, self.scenario_config["GEOPOLITICAL_SHOCK"])
        before_total = float(portfolio.get("total_value", 100_000_000))
        after_total = before_total
        asset_level = []

        for position in portfolio.get("positions", []):
            value = float(position["value"])
            class_name = position["asset_class"]
            loss_percent = 0.0
            if class_name == "Equities":
                loss_percent = cfg.get("equity_shock", 0.0)
            elif class_name == "Corporate Bonds":
                loss_percent = cfg.get("corporate_bond_shock", cfg.get("credit_spread_shock", 0.0))
            elif class_name == "Corporate Loans":
                loss_percent = cfg.get("loan_default_rate", 0.0)
            elif class_name == "Derivatives":
                loss_percent = cfg.get("derivative_haircut", 0.0)
            elif class_name == "Government Bonds":
                loss_percent = cfg.get("bond_price_shock", 0.0)
            elif class_name == "Cash":
                loss_percent = 0.0

            impacted = value * (loss_percent if loss_percent < 0 else 0.0)
            after_total += impacted
            asset_level.append({
                "asset_class": class_name,
                "before_value": value,
                "after_value": round(value + impacted, 2),
                "impact": round(impacted, 2),
            })

        abs_loss = before_total - after_total
        loss_pct = (abs_loss / before_total) * 100.0
        return {
            "scenario": scenario_name,
            "portfolio_before": round(before_total, 2),
            "portfolio_after": round(after_total, 2),
            "absolute_loss": round(abs_loss, 2),
            "loss_percentage": round(loss_pct, 2),
            "asset_level_impacts": asset_level,
            "triggered": True,
        }
