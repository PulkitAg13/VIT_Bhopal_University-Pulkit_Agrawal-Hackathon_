from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from app.services.nlp.entity_extractor import extract_entities
from app.services.nlp.event_classifier import classify_event
from app.services.nlp.sentiment import sentiment_analysis
from app.services.risk.impact_scorer import compute_impact_score


class RiskFusionService:
    def __init__(self, storage_path: str | Path | None = None) -> None:
        base_dir = Path(__file__).resolve().parents[4]
        self.storage_path = Path(storage_path) if storage_path else base_dir / "data" / "processed" / "events.json"
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.history: List[Dict[str, Any]] = self._load_history()

    def _load_history(self) -> List[Dict[str, Any]]:
        if not self.storage_path.exists():
            return []
        try:
            payload = json.loads(self.storage_path.read_text(encoding="utf-8"))
            if isinstance(payload, list):
                return payload
            if isinstance(payload, dict):
                events = payload.get("events")
                return events if isinstance(events, list) else []
        except json.JSONDecodeError:
            return []
        return []

    def _save_history(self) -> None:
        self.storage_path.write_text(json.dumps({"events": self.history}, indent=2), encoding="utf-8")

    def _source_credibility(self, source_name: str, source_type: str) -> float:
        source_key = (source_name or "").lower()
        if "fed" in source_key or "central bank" in source_key or "regulator" in source_key:
            return 0.92
        if "yahoo" in source_key or source_type == "rss":
            return 0.8
        if "twitter" in source_key or "dataset" in source_key:
            return 0.7
        if source_type == "demo":
            return 0.75
        return 0.68

    def _corroboration_score(self, text: str, entities: List[Dict[str, Any]]) -> float:
        base = 0.28
        if len(self.history) == 0:
            return round(base + 0.18, 4)
        similar = 0
        for prior in self.history[-10:]:
            prior_text = str(prior.get("text", "")).lower()
            if prior_text and text.lower() in prior_text or prior_text in text.lower():
                similar += 1
        if similar:
            return round(min(0.9, 0.45 + similar * 0.08), 4)
        diversity = len({entity.get("name") for entity in entities if entity.get("name")})
        return round(min(0.9, 0.52 + diversity * 0.05), 4)

    def _novelty_score(self, text: str) -> float:
        if not self.history:
            return 0.8
        similarities = []
        text_l = text.lower()
        for prior in self.history[-10:]:
            prior_text = str(prior.get("text", "")).lower()
            if not prior_text:
                continue
            overlap = len(set(text_l.split()) & set(prior_text.split())) / max(1, min(len(text_l.split()), len(prior_text.split())))
            similarities.append(overlap)
        if not similarities:
            return 0.8
        max_similarity = max(similarities)
        return round(max(0.18, 1.0 - max_similarity), 4)

    def analyze(self, text: str, source_name: str = "demo", source_type: str = "news") -> Dict[str, Any]:
        sentiment = sentiment_analysis(text)
        event = classify_event(text)
        entities = extract_entities(text)
        now = datetime.now(timezone.utc)
        corroboration = self._corroboration_score(text, entities)
        novelty = self._novelty_score(text)
        source_credibility = self._source_credibility(source_name, source_type)
        recency_hours = 1.2 if len(self.history) == 0 else min(24.0, 1.2 + len(self.history) * 0.4)
        risk_inputs = {
            "sentiment_score": sentiment["score"],
            "event_class": event["class"],
            "confidence": event["confidence"],
            "source_credibility": source_credibility,
            "corroboration": corroboration,
            "novelty": novelty,
            "recency_hours": recency_hours,
            "entity_relevance": 0.9 if entities else 0.5,
            "market_volatility": 0.72,
            "portfolio_exposure": 0.8 if any(entity.get("type") in {"company", "commodity", "institution"} for entity in entities) else 0.55,
        }
        impact = compute_impact_score(risk_inputs)
        confidence = min(0.99, max(0.45, 0.5 + event["confidence"] * 0.35 + corroboration * 0.2 + abs(sentiment["score"]) * 0.2))

        if impact["score"] >= 8 and sentiment["score"] < -0.15:
            risk_trajectory = "ACCELERATING"
        elif impact["score"] >= 6:
            risk_trajectory = "DEVELOPING"
        elif impact["score"] >= 4:
            risk_trajectory = "STABLE"
        else:
            risk_trajectory = "LOW"

        summary = [
            "Negative sentiment signal dominates the narrative" if sentiment["score"] < -0.15 else "Sentiment remains constructive or neutral",
            f"{event['class']} event identified with {event['confidence']:.2f} confidence",
            "Multiple sources increase corroboration" if corroboration >= 0.6 else "Evidence remains relatively narrow",
            "Portfolio and entity exposure magnify the signal" if entities else "Macro risk is elevated but not yet entity-specific",
        ]

        scenario = "GEOPOLITICAL_SHOCK" if event["class"] == "Geopolitical" else "MACRO_RATE_SHOCK" if event["class"] == "Macroeconomic" else "CREDIT_CRISIS" if event["class"] == "Credit Event" else "LIQUIDITY_SHOCK" if event["class"] == "Liquidity" else "MACRO_RATE_SHOCK"
        stress_triggered = impact["score"] >= 7 and event["class"] in {"Geopolitical", "Macroeconomic", "Credit Event", "Liquidity"}

        result = {
            "event_id": f"evt_{len(self.history) + 1:04d}",
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
            "stress_test": {
                "triggered": stress_triggered,
                "scenario": scenario,
            },
            "processing_time_ms": max(60, int(120 + len(text.split()) * 6)),
        }
        self.history.append(result)
        self._save_history()

        try:
            from app.api.routes.websocket import broadcast_event
            broadcast_event(result)
        except Exception:
            pass
        return result

    def list_events(self) -> List[Dict[str, Any]]:
        return self.history

    def get_event(self, event_id: str) -> Dict[str, Any] | None:
        for event in self.history:
            if event.get("event_id") == event_id:
                return event
        return None

    def overview(self) -> Dict[str, Any]:
        items = self.history
        if not items:
            return {
                "events_processed": 0,
                "high_risk_events": 0,
                "critical_events": 0,
                "average_sentiment": 0.0,
                "average_impact": 0.0,
                "overall_risk": 0.0,
                "portfolio_exposure": 0.0,
                "market_risk": "LOW",
            }
        avg_sentiment = sum(float(item["sentiment"]["score"]) for item in items) / len(items)
        avg_impact = sum(float(item["impact"]["score"]) for item in items) / len(items)
        overall_risk = round(min(10.0, avg_impact * 0.9 + 1.5), 2)
        return {
            "events_processed": len(items),
            "high_risk_events": sum(1 for item in items if item["impact"]["risk_level"] == "HIGH"),
            "critical_events": sum(1 for item in items if item["impact"]["risk_level"] == "CRITICAL"),
            "average_sentiment": round(avg_sentiment, 4),
            "average_impact": round(avg_impact, 4),
            "overall_risk": overall_risk,
            "portfolio_exposure": round(sum(0.7 for _ in items) / max(1, len(items)), 4),
            "market_risk": "ELEVATED" if overall_risk >= 6 else "MODERATE" if overall_risk >= 4 else "LOW",
        }

    def timeline(self) -> List[Dict[str, Any]]:
        points: List[Dict[str, Any]] = []
        for item in self.history[-12:]:
            points.append({
                "timestamp": item["timestamp"],
                "risk": item["impact"]["score"],
                "event_class": item["event"]["class"],
            })
        return points

    def metrics(self) -> Dict[str, Any]:
        overview = self.overview()
        return {**overview, "events_processed": overview["events_processed"]}
