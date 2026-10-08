"""
Explainable impact scoring framework for financial risk signals.

DISCLAIMER / METHODOLOGY:
This is an explainable expert-weighted prototype risk heuristic and NOT
a trained impact prediction model. There is no supervised ground-truth impact
dataset; weights are calibrated heuristics designed for transparent multi-factor
risk aggregation with complete component traceability.

Score range: 1.0 (minimal/negligible) to 10.0 (catastrophic/critical).
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("finrisk.impact_scorer")

# Event severity weights — relative systemic risk propensity by event category
EVENT_SEVERITY: Dict[str, float] = {
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

# Heuristic weights for component contributions (sum ~ 1.0)
WEIGHTS: Dict[str, float] = {
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
    """Map numeric score (1-10) to categorical risk level."""
    if score >= 9.0:
        return "CRITICAL"
    if score >= 7.0:
        return "HIGH"
    if score >= 4.0:
        return "MODERATE"
    return "LOW"


def compute_impact_score(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compute a transparent, explainable expert-weighted impact score.

    Validation rules:
    - No silent fake substitution of market volatility or portfolio exposure.
    - Unavailable components are explicitly flagged with 0.0 impact and listed
      in 'unavailable_components'.
    - Score is strictly clamped to [1.0, 10.0].

    Returns:
        {
            "score": float (1.0 - 10.0),
            "risk_level": "LOW" | "MODERATE" | "HIGH" | "CRITICAL",
            "components": {component: contribution},
            "raw_inputs": {...},
            "unavailable_components": [...],
            "methodology": "explainable expert-weighted prototype risk heuristic",
            "explanation": str
        }
    """
    unavailable_components: List[str] = []

    # Required / Core NLP inputs
    sentiment_score = float(payload.get("sentiment_score", 0.0))
    sentiment_score = max(-1.0, min(1.0, sentiment_score))

    event_class = str(payload.get("event_class", "Other"))
    if event_class not in EVENT_SEVERITY:
        event_class = "Other"

    confidence = float(payload.get("confidence", 0.5))
    confidence = max(0.0, min(1.0, confidence))

    source_credibility = float(payload.get("source_credibility", 0.7))
    source_credibility = max(0.0, min(1.0, source_credibility))

    corroboration = float(payload.get("corroboration", 0.2))
    corroboration = max(0.0, min(1.0, corroboration))

    novelty = float(payload.get("novelty", 0.8))
    novelty = max(0.0, min(1.0, novelty))

    recency_available = bool(payload.get("recency_available", True))
    raw_recency = payload.get("recency_hours")
    if not recency_available or raw_recency is None:
        recency_hours = None
        recency_raw = 0.0
        unavailable_components.append("recency")
    else:
        recency_hours = max(0.0, float(raw_recency))
        recency_raw = max(0.0, (1.0 - (recency_hours / 48.0))) * 10.0

    entity_relevance = float(payload.get("entity_relevance", 0.5))
    entity_relevance = max(0.0, min(1.0, entity_relevance))

    # Market context component: do NOT default to 0.5!
    market_context_available = bool(payload.get("market_context_available", True))
    raw_market_vol = payload.get("market_volatility")
    if not market_context_available or raw_market_vol is None:
        market_volatility = 0.0
        unavailable_components.append("market_volatility")
    else:
        market_volatility = max(0.0, min(1.0, float(raw_market_vol)))

    # Portfolio exposure component: do NOT default to 0.5!
    portfolio_available = bool(payload.get("portfolio_available", True))
    raw_exposure = payload.get("portfolio_exposure")
    if not portfolio_available or raw_exposure is None:
        portfolio_exposure = 0.0
        unavailable_components.append("portfolio_exposure")
    else:
        portfolio_exposure = max(0.0, min(1.0, float(raw_exposure)))

    # Compute raw component sub-scores (each scaled to 0-10)
    sentiment_raw = abs(sentiment_score) * 10.0
    event_severity_raw = (EVENT_SEVERITY[event_class] / 2.5) * max(0.4, confidence) * 10.0
    source_raw = source_credibility * 10.0
    corroboration_raw = corroboration * 10.0
    novelty_raw = novelty * 10.0
    entity_raw = entity_relevance * 10.0
    volatility_raw = market_volatility * 10.0
    exposure_raw = portfolio_exposure * 10.0

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

    final_score = round(max(1.0, min(10.0, raw_score)), 2)

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

    risk_level = get_risk_level(final_score)

    # Build clear, transparent explanation
    top_drivers = sorted(components.items(), key=lambda x: x[1], reverse=True)[:3]
    driver_strs = [f"{k.replace('_', ' ')} ({v:.2f})" for k, v in top_drivers]
    explanation = f"Impact score {final_score:.1f} ({risk_level}) driven primarily by: {', '.join(driver_strs)}"
    if unavailable_components:
        explanation += f". Note: {', '.join(unavailable_components)} unavailable (scored at 0.0)."

    return {
        "score": final_score,
        "risk_level": risk_level,
        "components": components,
        "unavailable_components": unavailable_components,
        "methodology": "explainable expert-weighted prototype risk heuristic",
        "explanation": explanation,
    }
