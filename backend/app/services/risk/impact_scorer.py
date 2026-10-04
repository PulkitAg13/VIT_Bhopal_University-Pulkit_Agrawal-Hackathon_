from __future__ import annotations

from typing import Dict

EVENT_WEIGHT = {
    "Geopolitical": 2.3,
    "Macroeconomic": 1.8,
    "Credit Event": 2.5,
    "Merger & Acquisition": 1.6,
    "Product Launch": 1.2,
    "Earnings": 1.4,
    "Regulatory / Legal": 2.1,
    "Monetary Policy": 1.9,
    "Commodity / Energy": 1.7,
    "Market Movement": 1.5,
    "Liquidity": 2.2,
    "Supply Chain": 1.8,
    "Management / Leadership": 1.3,
    "Corporate Action": 1.0,
    "Other": 0.9,
}


def get_risk_level(score: float) -> str:
    if score >= 9:
        return "CRITICAL"
    if score >= 7:
        return "HIGH"
    if score >= 4:
        return "MODERATE"
    return "LOW"


def compute_impact_score(payload: Dict[str, float | str]) -> Dict[str, object]:
    sentiment_score = float(payload.get("sentiment_score", 0.0))
    event_class = str(payload.get("event_class", "Other"))
    confidence = float(payload.get("confidence", 0.5))
    source_credibility = float(payload.get("source_credibility", 0.7))
    corroboration = float(payload.get("corroboration", 0.5))
    novelty = float(payload.get("novelty", 0.5))
    recency_hours = float(payload.get("recency_hours", 6.0))
    entity_relevance = float(payload.get("entity_relevance", 0.5))
    market_volatility = float(payload.get("market_volatility", 0.5))
    portfolio_exposure = float(payload.get("portfolio_exposure", 0.5))

    sentiment_component = abs(sentiment_score) * 3.2
    event_component = EVENT_WEIGHT.get(event_class, 1.0) * 1.1
    source_component = source_credibility * 2.0
    corroboration_component = corroboration * 2.5
    novelty_component = novelty * 1.7
    recency_component = max(0.0, 1.5 - (recency_hours / 24.0)) * 1.5
    entity_component = entity_relevance * 2.2
    volatility_component = market_volatility * 1.8
    exposure_component = portfolio_exposure * 2.0

    raw_score = (
        sentiment_component + event_component + source_component + corroboration_component + novelty_component
        + recency_component + entity_component + volatility_component + exposure_component + (confidence * 2.0)
    ) / 2.0
    score = max(1.0, min(10.0, raw_score))
    return {
        "score": round(score, 2),
        "risk_level": get_risk_level(score),
    }
