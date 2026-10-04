from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


def load_demo_events(path: str | Path) -> List[Dict[str, Any]]:
    data_path = Path(path)
    if not data_path.exists():
        return []
    with data_path.open("r", encoding="utf-8") as fh:
        payload = json.load(fh)
    return payload.get("events", [])


class DataSource:
    def __init__(self, name: str, source_type: str = "demo") -> None:
        self.name = name
        self.source_type = source_type

    def fetch(self) -> List[str]:
        return []


class DemoSource(DataSource):
    def __init__(self, path: str | Path) -> None:
        super().__init__("demo", "demo")
        self.path = Path(path)

    def fetch(self) -> List[str]:
        items = load_demo_events(self.path)
        return [item.get("text", "") for item in items if item.get("text")]


class RSSNewsSource(DataSource):
    def __init__(self, ticker: str) -> None:
        super().__init__(f"RSS:{ticker}", "rss")
        self.ticker = ticker

    def fetch(self) -> List[str]:
        return [
            f"{self.ticker} faces supply chain disruption as energy prices accelerate amid rising geopolitical tension.",
            f"{self.ticker} sees fresh concern over inflation and market volatility after federal policy signals.",
        ]


class DatasetSource(DataSource):
    def __init__(self, source_name: str) -> None:
        super().__init__(source_name, "dataset")

    def fetch(self) -> List[str]:
        return [
            "Fed signals aggressive rate increases amid persistent inflation pressure.",
            "Major banks face liquidity stress after credit spreads widen sharply.",
        ]
