from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


class PortfolioService:
    def __init__(self, portfolio_path: str | Path | None = None) -> None:
        self.portfolio_path = Path(portfolio_path) if portfolio_path else Path(__file__).resolve().parents[4] / "data" / "synthetic" / "portfolio.json"

    def load_portfolio(self) -> Dict[str, Any]:
        if not self.portfolio_path.exists():
            return self._default_portfolio()
        with self.portfolio_path.open("r", encoding="utf-8") as fh:
            return json.load(fh)

    def _default_portfolio(self) -> Dict[str, Any]:
        return {
            "portfolio_id": "wholesale-demo",
            "name": "Synthetic Wholesale Banking Portfolio",
            "total_value": 100000000,
            "positions": [
                {"asset_class": "Corporate Loans", "value": 30000000, "exposure": 0.8},
                {"asset_class": "Government Bonds", "value": 20000000, "exposure": 0.4},
                {"asset_class": "Corporate Bonds", "value": 15000000, "exposure": 0.7},
                {"asset_class": "Equities", "value": 20000000, "exposure": 0.9},
                {"asset_class": "Derivatives", "value": 10000000, "exposure": 0.8},
                {"asset_class": "Cash", "value": 5000000, "exposure": 0.2},
            ],
        }
