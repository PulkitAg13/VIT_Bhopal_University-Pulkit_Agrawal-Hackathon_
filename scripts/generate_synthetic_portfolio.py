from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "synthetic"
OUT_DIR.mkdir(parents=True, exist_ok=True)

portfolio = {
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

(OUT_DIR / "portfolio.json").write_text(json.dumps(portfolio, indent=2), encoding="utf-8")
with (OUT_DIR / "portfolio.csv").open("w", newline="", encoding="utf-8") as fh:
    writer = csv.DictWriter(fh, fieldnames=["asset_class", "value", "exposure"])
    writer.writeheader()
    writer.writerows(portfolio["positions"])

print("Synthetic portfolio generated.")
