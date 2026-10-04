from __future__ import annotations

from typing import Dict, List

EVENT_KEYWORDS = {
    "Geopolitical": ["war", "sanction", "embargo", "geopolitics", "conflict", "energy supply", "tariff", "tension", "shipping route"],
    "Macroeconomic": ["inflation", "rate hike", "recession", "gdp", "cpi", "bond yield", "unemployment"],
    "Credit Event": ["default", "downgrade", "credit stress", "nonperforming", "debt restructuring", "credit rating"],
    "Merger & Acquisition": ["merger", "acquisition", "takeover", "deal", "buyout"],
    "Product Launch": ["launch", "product debut", "release", "new device", "chip launch"],
    "Earnings": ["earnings", "quarterly results", "revenue", "eps", "profit beat"],
    "Regulatory / Legal": ["investigation", "regulator", "lawsuit", "compliance", "probe", "penalty"],
    "Monetary Policy": ["fed", "rate cut", "rate increase", "central bank", "policy"],
    "Commodity / Energy": ["oil", "gas", "energy", "commodity", "crude", "natural gas"],
    "Market Movement": ["rally", "selloff", "stock slide", "equity drop", "market crash"],
    "Liquidity": ["liquidity", "cash crunch", "funding", "credit squeeze", "bank run"],
    "Supply Chain": ["supply", "disruption", "shipping", "logistics", "chip shortage", "port congestion"],
    "Management / Leadership": ["ceo", "management", "leadership", "board", "executive change", "succession"],
    "Corporate Action": ["dividend", "stock split", "share repurchase", "capital raise"],
}


def classify_event(text: str) -> Dict[str, object]:
    lowered = text.lower()
    hits: List[tuple[str, int]] = []
    for event_class, keywords in EVENT_KEYWORDS.items():
        count = sum(1 for keyword in keywords if keyword in lowered)
        if count:
            hits.append((event_class, count))
    if not hits:
        return {"class": "Other", "confidence": 0.45, "support": []}

    event_class, max_count = max(hits, key=lambda item: item[1])
    confidence = min(0.97, 0.6 + (max_count / max(1, len(EVENT_KEYWORDS[event_class]))) * 0.35)
    return {"class": event_class, "confidence": round(confidence, 4), "support": [event_class]}
