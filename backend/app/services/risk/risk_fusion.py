from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Dict, List

from app.services.nlp.entity_extractor import extract_entities
from app.services.nlp.event_classifier import classify_event
from app.services.nlp.sentiment import sentiment_analysis
from app.services.risk.impact_scorer import compute_impact_score


class RiskFusionService:
    def __init__(self) -> None:
        self.history: List[Dict[str, Any]] = []

    def analyze(self, text: str, source_name: str = "demo", source_type: str = "news") -> Dict[str, Any]:
        sentiment = sentiment_analysis(text)
        event = classify_event(text)
        entities = extract_entities(text)
        now = datetime.now(timezone.utc)
        corroboration = 0.55
        novelty = 0.72
        if any(entity.get("type") in {"institution", "company"} for entity in entities):
            novelty = 0.8

        source_credibility = 0.8 if source_type in {"official", "filing", "rss"} else 0.68
        risk_inputs = {
            "sentiment_score": sentiment["score"],
            "event_class": event["class"],
            "confidence": event["confidence"],
            "source_credibility": source_credibility,
            "corroboration": corroboration,
            "novelty": novelty,
            "recency_hours": 2.0,
            "entity_relevance": 0.8,
            "market_volatility": 0.75,
            "portfolio_exposure": 0.7,
        }
        impact = compute_impact_score(risk_inputs)
        confidence = min(0.99, max(0.45, 0.5 + event["confidence"] * 0.4 + corroboration * 0.2 + abs(sentiment["score"]) * 0.2))

        if impact["score"] >= 7 and sentiment["score"] < 0:
            risk_trajectory = "ACCELERATING"
        else:
            risk_trajectory = "STABLE"

        summary = [
            "Strong negative financial sentiment" if sentiment["score"] < -0.15 else "Positive or neutral sentiment signal",
            f"High-severity {event['class']} event" if impact["score"] >= 7 else f"{event['class']} event with moderate impact",
            "Multiple sources corroborate the event" if corroboration > 0.7 else "Single-source signal with limited corroboration",
            "Material entity and portfolio exposure detected" if entities else "General macro risk signal",
        ]
        result = {
            "event_id": f"evt_{len(self.history)+1:04d}",
            "timestamp": now.isoformat(),
            "source": {"type": source_type, "name": source_name},
            "text": text,
            "entities": entities,
            "sentiment": {
                "label": sentiment["label"],
                "score": sentiment["score"],
                "confidence": sentiment["confidence"],
                "probabilities": sentiment["probabilities"],
            },
            "event": {"class": event["class"], "confidence": event["confidence"]},
            "impact": {"score": impact["score"], "risk_level": impact["risk_level"]},
            "novelty_score": round(novelty, 4),
            "corroboration_score": round(corroboration, 4),
            "confidence_score": round(confidence, 4),
            "risk_trajectory": risk_trajectory,
            "explanation": summary,
            "stress_test": {"triggered": impact["score"] >= 7 and event["class"] in {"Geopolitical", "Macroeconomic", "Credit Event", "Liquidity"}, "scenario": "GEOPOLITICAL_SHOCK" if event["class"] == "Geopolitical" else "MACRO_RATE_SHOCK" if event["class"] == "Macroeconomic" else "CREDIT_CRISIS" if event["class"] == "Credit Event" else "LIQUIDITY_SHOCK"},
            "processing_time_ms": 180,
        }
        self.history.append(result)
        return result
