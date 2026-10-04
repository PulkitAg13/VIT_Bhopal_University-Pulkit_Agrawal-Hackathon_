"""
Explainable impact scoring for financial risk signals.

Computes a 1-10 impact score with individual component contributions,
enabling transparent "Why this score?" explanations.
"""
from __future__ import annotations

from typing import Any, Dict

# Event severity weights — how impactful each event type inherently is
EVENT_SEVERITY = {
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

# Component weights for the final score (normalized to sum ~10)
WEIGHTS = {
    "sentiment": 0.15,
    "event_severity": 0.18,
    "source_credibility": 0.10,
    "corroboration": 0.12,
    "novelty": 0.10,
    "recency": 0.08,
    "entity_relevance": 0.10,
    "market_volatility": 0.07,
    "portfolio_exposure": 0.10,
}


def get_risk_level(score: float) -> str:
    if score >= 9:
        return "CRITICAL"
    if score >= 7:
        return "HIGH"
    if score >= 4:
        return "MODERATE"
    return "LOW"


def compute_impact_score(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compute a transparent, explainable impact score.

    Args:
        payload: dict with keys like sentiment_score, event_class,
                 confidence, source_credibility, corroboration,
                 novelty, recency_hours, entity_relevance,
                 market_volatility, portfolio_exposure

    Returns:
        {
            "score": float (1-10),
            "risk_level": str,
            "components": {component: contribution},
            "explanation": str
        }
    """
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

    # Compute raw component scores (each normalized to ~0-10 range)
    sentiment_raw = abs(sentiment_score) * 10.0  # 0-10
    event_severity_raw = EVENT_SEVERITY.get(event_class, 1.0) * confidence * 4.0  # 0-10
    source_raw = source_credibility * 10.0  # 0-10
    corroboration_raw = corroboration * 10.0  # 0-10
    novelty_raw = novelty * 10.0  # 0-10
    recency_raw = max(0.0, (1.0 - recency_hours / 48.0)) * 10.0  # 0-10, decays over 48h
    entity_raw = entity_relevance * 10.0  # 0-10
    volatility_raw = market_volatility * 10.0  # 0-10
    exposure_raw = portfolio_exposure * 10.0  # 0-10

    # Weighted combination
    raw_score = (
        WEIGHTS["sentiment"] * sentiment_raw
        + WEIGHTS["event_severity"] * event_severity_raw
        + WEIGHTS["source_credibility"] * source_raw
        + WEIGHTS["corroboration"] * corroboration_raw
        + WEIGHTS["novelty"] * novelty_raw
        + WEIGHTS["recency"] * recency_raw
        + WEIGHTS["entity_relevance"] * entity_raw
        + WEIGHTS["market_volatility"] * volatility_raw
        + WEIGHTS["portfolio_exposure"] * exposure_raw
    )

    score = max(1.0, min(10.0, raw_score))

    # Component contributions (how much each contributed to final score)
    components = {
        "sentiment": round(WEIGHTS["sentiment"] * sentiment_raw, 2),
        "event_severity": round(WEIGHTS["event_severity"] * event_severity_raw, 2),
        "source_credibility": round(WEIGHTS["source_credibility"] * source_raw, 2),
        "corroboration": round(WEIGHTS["corroboration"] * corroboration_raw, 2),
        "novelty": round(WEIGHTS["novelty"] * novelty_raw, 2),
        "recency": round(WEIGHTS["recency"] * recency_raw, 2),
        "entity_relevance": round(WEIGHTS["entity_relevance"] * entity_raw, 2),
        "market_volatility": round(WEIGHTS["market_volatility"] * volatility_raw, 2),
        "portfolio_exposure": round(WEIGHTS["portfolio_exposure"] * exposure_raw, 2),
    }

    risk_level = get_risk_level(score)

    # Generate explanation
    top_drivers = sorted(components.items(), key=lambda x: x[1], reverse=True)[:3]
    driver_strs = [f"{k.replace('_', ' ')} ({v:.1f})" for k, v in top_drivers]

    return {
        "score": round(score, 2),
        "risk_level": risk_level,
        "components": components,
        "explanation": f"Impact driven by: {', '.join(driver_strs)}",
    }
