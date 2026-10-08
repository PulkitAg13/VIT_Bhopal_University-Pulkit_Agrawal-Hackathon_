"""
Event classification using zero-shot classification.

Uses facebook/bart-large-mnli via the ModelManager singleton for
classification into the canonical financial event taxonomy.
"""
from __future__ import annotations

from typing import Any, Dict

from app.core.model_manager import get_model_manager


def classify_event(text: str) -> Dict[str, Any]:
    """Classify a financial text into the canonical event taxonomy.

    Returns:
        {
            "class": str,
            "confidence": float,
            "all_scores": dict,
            "model": str
        }
    """
    mm = get_model_manager()
    return mm.classify_event(text)
