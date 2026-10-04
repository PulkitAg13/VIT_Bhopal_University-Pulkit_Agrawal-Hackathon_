from __future__ import annotations

import re
from typing import Dict, List

ENTITY_MAP = {
    "apple": {"name": "Apple Inc.", "ticker": "AAPL", "type": "company"},
    "apple inc": {"name": "Apple Inc.", "ticker": "AAPL", "type": "company"},
    "microsoft": {"name": "Microsoft", "ticker": "MSFT", "type": "company"},
    "nvidia": {"name": "NVIDIA", "ticker": "NVDA", "type": "company"},
    "tesla": {"name": "Tesla", "ticker": "TSLA", "type": "company"},
    "amazon": {"name": "Amazon", "ticker": "AMZN", "type": "company"},
    "meta": {"name": "Meta", "ticker": "META", "type": "company"},
    "google": {"name": "Alphabet Inc.", "ticker": "GOOGL", "type": "company"},
    "jpmorgan": {"name": "JPMorgan Chase", "ticker": "JPM", "type": "institution"},
    "bank of america": {"name": "Bank of America", "ticker": "BAC", "type": "institution"},
    "fed": {"name": "Federal Reserve", "ticker": "FED", "type": "institution"},
    "us federal reserve": {"name": "Federal Reserve", "ticker": "FED", "type": "institution"},
    "eurozone": {"name": "Eurozone", "ticker": None, "type": "region"},
    "oil": {"name": "Crude Oil", "ticker": "CL=F", "type": "commodity"},
    "gold": {"name": "Gold", "ticker": "GC=F", "type": "commodity"},
    "us dollar": {"name": "US Dollar", "ticker": "USD", "type": "currency"},
    "yen": {"name": "Japanese Yen", "ticker": "JPY", "type": "currency"},
    "regulator": {"name": "Regulator", "ticker": None, "type": "institution"},
}


def extract_entities(text: str) -> List[Dict[str, object]]:
    lowered = text.lower()
    found: List[Dict[str, object]] = []
    seen: set[str] = set()
    for key, details in ENTITY_MAP.items():
        if key in lowered and key not in seen:
            seen.add(key)
            found.append({
                "name": details["name"],
                "ticker": details["ticker"],
                "type": details["type"],
                "confidence": 0.85,
            })

    for match in re.findall(r"\b[A-Z]{1,5}\b", text):
        if match in {"AAPL", "MSFT", "NVDA", "TSLA", "AMZN", "META", "GOOGL", "JPM", "BAC", "USD", "FED"}:
            details = next((item for item in ENTITY_MAP.values() if item.get("ticker") == match), None)
            if details and match not in seen:
                found.append({"name": details["name"], "ticker": match, "type": details["type"], "confidence": 0.9})
                seen.add(match)

    if not found:
        found.append({"name": "General Market", "ticker": None, "type": "macro", "confidence": 0.5})
    return found
