from __future__ import annotations

import re
from typing import Dict, List, Tuple

NEGATIVE_WORDS = [
    "decline", "drop", "fall", "downgrade", "loss", "default", "liquidity", "risk", "stress",
    "fraud", "fraudulent", "shock", "supply", "disruption", "recession", "inflation", "warning",
    "collapse", "investigation", "sanction", "bankruptcy", "insolvency", "exposure", "margin",
    "shortfall", "volatility", "concern", "tension", "escalating", "regulatory", "bearish", "downward",
]
POSITIVE_WORDS = [
    "growth", "gain", "upgrade", "strength", "profit", "expansion", "positive", "bullish", "rally",
    "surge", "stable", "improvement", "resilience", "strong", "healthy", "increase", "recovery",
    "momentum", "optimism", "confidence", "dividend", "boost", "rebound", "solid"
]


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def sentiment_analysis(text: str) -> Dict[str, object]:
    norm = normalize_text(text)
    negatives = sum(1 for word in NEGATIVE_WORDS if word in norm)
    positives = sum(1 for word in POSITIVE_WORDS if word in norm)
    total = negatives + positives

    raw_score = 0.0
    if total:
        raw_score = (positives - negatives) / total
    else:
        raw_score = 0.0

    score = max(-1.0, min(1.0, raw_score))
    if score > 0.15:
        label = "positive"
    elif score < -0.15:
        label = "negative"
    else:
        label = "neutral"

    confidence = min(0.99, 0.55 + abs(score) * 0.45)
    probabilities = {
        "positive": max(0.0, min(1.0, 0.5 + score / 2.0)),
        "negative": max(0.0, min(1.0, 0.5 - score / 2.0)),
        "neutral": max(0.0, min(1.0, 1.0 - abs(score))),
    }
    probabilities = {k: round(v, 4) for k, v in probabilities.items()}
    return {
        "label": label,
        "score": round(score, 4),
        "confidence": round(confidence, 4),
        "probabilities": probabilities,
    }
