"""
FinBERT-powered financial sentiment analysis.

Uses ProsusAI/finbert via the ModelManager singleton.
Falls back to keyword-based analysis if the model is unavailable.
"""
from __future__ import annotations

from typing import Any, Dict

from app.core.model_manager import get_model_manager


def sentiment_analysis(text: str) -> Dict[str, Any]:
    """Analyze financial sentiment using FinBERT.

    Returns:
        {
            "label": "positive" | "negative" | "neutral",
            "score": float (-1 to +1),
            "confidence": float (0 to 1),
            "probabilities": {"positive": ..., "negative": ..., "neutral": ...},
            "model": str
        }
    """
    mm = get_model_manager()
    return mm.analyze_sentiment(text)
