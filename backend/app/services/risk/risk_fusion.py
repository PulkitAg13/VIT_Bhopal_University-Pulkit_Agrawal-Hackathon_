"""
Risk Fusion Service — Core pipeline that transforms financial text
through the complete NLP + risk assessment pipeline.

Pipeline: Text → Sentiment → Entity Extraction → Event Classification →
          Embedding → Dedup/Clustering → Corroboration → Novelty →
          Impact Scoring → Risk Level → DB Persistence → WebSocket → Stress Trigger
"""
from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import numpy as np
from sqlalchemy.orm import Session

from app.core.model_manager import get_model_manager
from app.core.redis_client import publish_event
from app.models import (
    Document, DocumentEntity, Entity, EventCluster,
    RiskSignal, Source, StressSimulation,
)
from app.services.nlp.entity_extractor import extract_entities
from app.services.nlp.event_classifier import classify_event
from app.services.nlp.sentiment import sentiment_analysis
from app.services.risk.impact_scorer import compute_impact_score

logger = logging.getLogger("finrisk.risk_fusion")

# Source credibility profiles — clearly labelled as prototype assumptions
SOURCE_CREDIBILITY = {
    "official_regulator": {"score": 0.92, "label": "Official regulatory source"},
    "central_bank": {"score": 0.90, "label": "Central bank communication"},
    "company_filing": {"score": 0.88, "label": "Company filing / press release"},
    "major_financial_news": {"score": 0.82, "label": "Major financial newswire"},
    "general_news": {"score": 0.72, "label": "General news source"},
    "social_media": {"score": 0.55, "label": "Social media / unverified"},
    "rss": {"score": 0.78, "label": "RSS news feed"},
    "dataset": {"score": 0.65, "label": "Dataset replay"},
    "demo": {"score": 0.70, "label": "Synthetic demo data"},
}

# Clustering threshold
SIMILARITY_THRESHOLD = 0.75


class RiskFusionService:
    """Stateless service — all state goes to PostgreSQL."""

    def __init__(self) -> None:
        self.mm = get_model_manager()

    def _get_source_credibility(self, source_name: str, source_type: str) -> Dict[str, Any]:
        """Determine source credibility based on type and name. Clearly labelled as prototype."""
        key = source_type.lower()
        name_lower = (source_name or "").lower()

        # Override by name
        if any(kw in name_lower for kw in ["fed", "central bank", "regulator", "sec"]):
            profile = SOURCE_CREDIBILITY["official_regulator"]
        elif any(kw in name_lower for kw in ["yahoo", "reuters", "bloomberg"]):
            profile = SOURCE_CREDIBILITY["major_financial_news"]
        elif key in SOURCE_CREDIBILITY:
            profile = SOURCE_CREDIBILITY[key]
        else:
            profile = SOURCE_CREDIBILITY.get("general_news", {"score": 0.68, "label": "Unknown"})

        return {
            "score": profile["score"],
            "label": profile["label"],
            "note": "Prototype source credibility assumption",
        }

    def _compute_novelty(self, embedding: np.ndarray, db: Session) -> float:
        """Calculate novelty: 1 - max_similarity with recent events."""
        recent_signals = (
            db.query(RiskSignal)
            .join(Document)
            .filter(Document.embedding_vector.isnot(None))
            .order_by(RiskSignal.created_at.desc())
            .limit(20)
            .all()
        )
        if not recent_signals:
            return 0.85

        max_sim = 0.0
        for signal in recent_signals:
            doc = signal.document
            if doc.embedding_vector:
                prior_emb = np.array(doc.embedding_vector, dtype=np.float32)
                sim = self.mm.cosine_similarity(embedding, prior_emb)
                max_sim = max(max_sim, sim)

        novelty = max(0.1, 1.0 - max_sim)
        return round(novelty, 4)

    def _compute_corroboration(
        self, embedding: np.ndarray, source_name: str, db: Session
    ) -> Dict[str, Any]:
        """Calculate corroboration based on independent source count and diversity."""
        recent = (
            db.query(RiskSignal)
            .join(Document)
            .filter(Document.embedding_vector.isnot(None))
            .order_by(RiskSignal.created_at.desc())
            .limit(30)
            .all()
        )
        if not recent:
            return {"score": round(0.3, 4), "independent_sources": 0, "similar_events": 0}

        similar_sources = set()
        similar_count = 0
        for signal in recent:
            doc = signal.document
            if doc.embedding_vector:
                prior_emb = np.array(doc.embedding_vector, dtype=np.float32)
                sim = self.mm.cosine_similarity(embedding, prior_emb)
                if sim >= 0.6:
                    similar_count += 1
                    if signal.source_name and signal.source_name.lower() != source_name.lower():
                        similar_sources.add(signal.source_name)

        independent = len(similar_sources)
        # Score based on independent sources and similar events
        base = 0.25
        source_bonus = min(0.4, independent * 0.12)
        event_bonus = min(0.25, similar_count * 0.05)
        score = min(0.95, base + source_bonus + event_bonus)

        return {
            "score": round(score, 4),
            "independent_sources": independent,
            "similar_events": similar_count,
        }

    def _find_or_create_cluster(
        self, embedding: np.ndarray, event_class: str, db: Session
    ) -> Optional[EventCluster]:
        """Find existing cluster or create new one based on semantic similarity."""
        recent_clusters = (
            db.query(EventCluster)
            .filter(EventCluster.status.in_(["NEW", "DEVELOPING", "ESCALATING", "STABLE"]))
            .order_by(EventCluster.last_updated.desc())
            .limit(20)
            .all()
        )

        best_cluster = None
        best_sim = 0.0

        for cluster in recent_clusters:
            if cluster.centroid_embedding:
                centroid = np.array(cluster.centroid_embedding, dtype=np.float32)
                sim = self.mm.cosine_similarity(embedding, centroid)
                if sim > best_sim:
                    best_sim = sim
                    best_cluster = cluster

        if best_cluster and best_sim >= SIMILARITY_THRESHOLD:
            # Update existing cluster
            best_cluster.event_count += 1
            best_cluster.last_updated = datetime.now(timezone.utc)
            # Update status based on event count
            if best_cluster.event_count >= 5:
                best_cluster.status = "ESCALATING"
            elif best_cluster.event_count >= 3:
                best_cluster.status = "DEVELOPING"
            return best_cluster

        # Create new cluster
        cluster = EventCluster(
            id=str(uuid.uuid4()),
            label=event_class,
            representative_text=None,
            status="NEW",
            event_count=1,
            centroid_embedding=embedding.tolist(),
        )
        db.add(cluster)
        return cluster

    def analyze(
        self,
        text: str,
        source_name: str = "demo",
        source_type: str = "news",
        source_url: str | None = None,
        published_at: datetime | None = None,
        db: Session = None,
    ) -> Dict[str, Any]:
        """Full pipeline: NLP → Risk Assessment → DB Persistence → WebSocket."""
        t0 = time.time()

        # 1. NLP: Sentiment
        sentiment = sentiment_analysis(text)

        # 2. NLP: Entity extraction
        entities = extract_entities(text)

        # 3. NLP: Event classification
        event = classify_event(text)

        # 4. Embedding
        embedding = self.mm.encode([text])[0]

        # 5. Source credibility
        cred = self._get_source_credibility(source_name, source_type)

        if db is not None:
            # 6. Novelty (requires DB)
            novelty = self._compute_novelty(embedding, db)

            # 7. Corroboration (requires DB)
            corrob = self._compute_corroboration(embedding, source_name, db)

            # 8. Clustering
            cluster = self._find_or_create_cluster(embedding, event["class"], db)
        else:
            novelty = 0.8
            corrob = {"score": 0.3, "independent_sources": 0, "similar_events": 0}
            cluster = None

        # 9. Entity relevance
        entity_relevance = 0.9 if any(
            e.get("type") in {"company", "institution", "commodity"} for e in entities
        ) else 0.5

        # 10. Impact scoring
        risk_inputs = {
            "sentiment_score": sentiment["score"],
            "event_class": event["class"],
            "confidence": event["confidence"],
            "source_credibility": cred["score"],
            "corroboration": corrob["score"],
            "novelty": novelty,
            "recency_hours": 1.0,
            "entity_relevance": entity_relevance,
            "market_volatility": 0.5,  # Documented fallback
            "portfolio_exposure": 0.7 if entity_relevance > 0.6 else 0.4,
        }
        impact = compute_impact_score(risk_inputs)

        # 11. Overall confidence
        overall_confidence = min(
            0.99,
            max(0.35, 0.4 + event["confidence"] * 0.3 + corrob["score"] * 0.15 + abs(sentiment["score"]) * 0.15)
        )

        # 12. Risk trajectory
        if impact["score"] >= 8 and sentiment["score"] < -0.15:
            risk_trajectory = "ACCELERATING"
        elif impact["score"] >= 6:
            risk_trajectory = "DEVELOPING"
        elif impact["score"] >= 4:
            risk_trajectory = "STABLE"
        else:
            risk_trajectory = "LOW"

        # 13. Explanation
        explanation = [
            f"Sentiment: {sentiment['label']} ({sentiment['score']:+.2f}) via {sentiment.get('model', 'unknown')}",
            f"Event: {event['class']} ({event['confidence']:.2f} confidence) via {event.get('model', 'unknown')}",
            f"Source credibility: {cred['score']:.2f} — {cred['label']}",
            f"Corroboration: {corrob['score']:.2f} ({corrob['independent_sources']} independent sources)",
            f"Novelty: {novelty:.2f}",
            impact["explanation"],
        ]

        # 14. Stress trigger logic
        scenario_map = {
            "Geopolitical": "GEOPOLITICAL_SHOCK",
            "Macroeconomic": "MACRO_RATE_SHOCK",
            "Credit Event": "CREDIT_CRISIS",
            "Liquidity": "LIQUIDITY_SHOCK",
            "Commodity / Energy": "COMMODITY_SHOCK",
            "Monetary Policy": "MACRO_RATE_SHOCK",
        }
        scenario = scenario_map.get(event["class"], "MACRO_RATE_SHOCK")
        stress_triggered = impact["score"] >= 7.0 and event["class"] in scenario_map

        processing_time = int((time.time() - t0) * 1000)

        # 15. Persist to database
        signal_id = str(uuid.uuid4())
        doc_id = str(uuid.uuid4())

        if db is not None:
            # Create/find source
            source_record = db.query(Source).filter(
                Source.name == source_name, Source.source_type == source_type
            ).first()
            if not source_record:
                source_record = Source(
                    id=str(uuid.uuid4()),
                    name=source_name,
                    source_type=source_type,
                    credibility_score=cred["score"],
                    url=source_url,
                )
                db.add(source_record)

            # Create document
            doc = Document(
                id=doc_id,
                source_id=source_record.id,
                original_text=text,
                source_url=source_url,
                published_at=published_at,
                embedding_vector=embedding.tolist(),
            )
            db.add(doc)

            # Create/update entities
            for ent in entities:
                entity_record = db.query(Entity).filter(
                    Entity.canonical_name == ent["canonical_name"]
                ).first()
                if not entity_record:
                    entity_record = Entity(
                        id=str(uuid.uuid4()),
                        canonical_name=ent["canonical_name"],
                        ticker=ent.get("ticker"),
                        entity_type=ent["type"],
                    )
                    db.add(entity_record)
                    db.flush()

                doc_entity = DocumentEntity(
                    id=str(uuid.uuid4()),
                    document_id=doc_id,
                    entity_id=entity_record.id,
                    confidence=ent["confidence"],
                )
                db.add(doc_entity)

            # Create risk signal
            signal = RiskSignal(
                id=signal_id,
                document_id=doc_id,
                event_cluster_id=cluster.id if cluster else None,
                sentiment_label=sentiment["label"],
                sentiment_score=sentiment["score"],
                sentiment_confidence=sentiment["confidence"],
                sentiment_probabilities=sentiment.get("probabilities"),
                event_class=event["class"],
                event_confidence=event["confidence"],
                impact_score=impact["score"],
                impact_components=impact["components"],
                risk_level=impact["risk_level"],
                overall_confidence=round(overall_confidence, 4),
                novelty_score=round(novelty, 4),
                corroboration_score=corrob["score"],
                risk_trajectory=risk_trajectory,
                source_name=source_name,
                source_type=source_type,
                source_credibility=cred["score"],
                explanation=explanation,
                processing_time_ms=processing_time,
                market_context_available=False,
                status="NEW",
            )
            db.add(signal)
            db.commit()
            db.refresh(signal)

        # Build response
        result = {
            "signal_id": signal_id,
            "document_id": doc_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": {"type": source_type, "name": source_name, "url": source_url},
            "text": text,
            "entities": entities,
            "sentiment": sentiment,
            "event": {"class": event["class"], "confidence": event["confidence"], "model": event.get("model")},
            "impact": {
                "score": impact["score"],
                "risk_level": impact["risk_level"],
                "components": impact["components"],
                "explanation": impact["explanation"],
            },
            "novelty_score": round(novelty, 4),
            "corroboration": corrob,
            "confidence_score": round(overall_confidence, 4),
            "risk_trajectory": risk_trajectory,
            "explanation": explanation,
            "stress_test": {
                "triggered": stress_triggered,
                "scenario": scenario if stress_triggered else None,
            },
            "processing_time_ms": processing_time,
            "market_context_available": False,
            "cluster_id": cluster.id if cluster else None,
            "cluster_status": cluster.status if cluster else None,
        }

        # 16. Publish to Redis for WebSocket
        publish_event(result)

        return result
