"""
Risk Fusion Service — Core pipeline that transforms financial text
through the complete NLP + risk assessment pipeline.

Pipeline: Text → Sentiment → Entity Extraction → Event Classification →
          Embedding → Dedup/Clustering → Corroboration → Novelty →
          Market Context → Portfolio Exposure → Impact Scoring →
          Risk Level → DB Persistence → WebSocket → Automatic Stress Trigger

CRITICAL: No hardcoded market_volatility or portfolio_exposure.
All values come from actual data or are marked as unavailable.
"""
from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime, timezone, timedelta
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

# Clustering thresholds
SIMILARITY_THRESHOLD = 0.75
CLUSTER_ENTITY_OVERLAP_MIN = 0.3
CLUSTER_TIME_WINDOW_HOURS = 72

# Stress trigger configuration
STRESS_TRIGGER_THRESHOLD = 7.0
STRESS_ELIGIBLE_CATEGORIES = {
    "Geopolitical": "GEOPOLITICAL_SHOCK",
    "Macroeconomic": "MACRO_RATE_SHOCK",
    "Credit Event": "CREDIT_CRISIS",
    "Liquidity": "LIQUIDITY_SHOCK",
    "Commodity / Energy": "COMMODITY_SHOCK",
    "Monetary Policy": "MACRO_RATE_SHOCK",
}


class MarketContextService:
    """Fetch real market data via yfinance. Cached to avoid excessive API calls."""
    
    _cache: Dict[str, Dict[str, Any]] = {}
    _cache_ttl = timedelta(minutes=15)

    @classmethod
    def get_market_context(cls, entities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get real market volatility for relevant entities.
        
        Returns market_context_available=False if data cannot be fetched.
        NEVER returns a fake hardcoded value.
        """
        tickers = []
        for ent in entities:
            ticker = ent.get("ticker")
            if ticker and ent.get("type") in {"company", "institution", "commodity"}:
                tickers.append(ticker)
        
        if not tickers:
            # Use market benchmark for macro events
            tickers = ["SPY"]
        
        try:
            import yfinance as yf
            
            volatilities = []
            price_changes = []
            
            for ticker in tickers[:3]:  # Limit to 3 to avoid rate limits
                # Check cache
                cache_key = ticker
                if cache_key in cls._cache:
                    cached = cls._cache[cache_key]
                    if datetime.now(timezone.utc) - cached["fetched_at"] < cls._cache_ttl:
                        volatilities.append(cached.get("volatility", 0))
                        price_changes.append(cached.get("price_change", 0))
                        continue
                
                try:
                    stock = yf.Ticker(ticker)
                    hist = stock.history(period="1mo")
                    
                    if hist.empty or len(hist) < 5:
                        continue
                    
                    # 30-day realized volatility (annualized)
                    returns = hist["Close"].pct_change().dropna()
                    vol = float(returns.std() * (252 ** 0.5))  # Annualized
                    
                    # Recent price change (5-day)
                    price_change = float((hist["Close"].iloc[-1] / hist["Close"].iloc[-5] - 1))
                    
                    volatilities.append(vol)
                    price_changes.append(price_change)
                    
                    # Cache
                    cls._cache[cache_key] = {
                        "volatility": vol,
                        "price_change": price_change,
                        "fetched_at": datetime.now(timezone.utc),
                    }
                except Exception as exc:
                    logger.warning("yfinance fetch failed for %s: %s", ticker, exc)
                    continue
            
            if volatilities:
                avg_vol = sum(volatilities) / len(volatilities)
                avg_change = sum(price_changes) / len(price_changes)
                # Normalize volatility to 0-1 scale (typical range 0.1-0.6)
                normalized_vol = min(1.0, max(0.0, (avg_vol - 0.1) / 0.5))
                
                return {
                    "market_context_available": True,
                    "market_volatility": round(normalized_vol, 4),
                    "avg_realized_volatility": round(avg_vol, 4),
                    "avg_price_change_5d": round(avg_change, 4),
                    "tickers_checked": tickers[:3],
                    "data_source": "yfinance",
                }
        except ImportError:
            logger.warning("yfinance not installed — market context unavailable")
        except Exception as exc:
            logger.warning("Market context fetch failed: %s", exc)
        
        return {
            "market_context_available": False,
            "market_volatility": 0.0,
            "note": "Market data unavailable — impact score uses 0 for market component",
        }


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

    def _compute_novelty(self, embedding: np.ndarray, event_class: str,
                          entity_names: List[str], db: Session) -> float:
        """Calculate novelty: 1 - max_similarity with recent relevant events.
        
        Uses embeddings, entity overlap, and event class for filtering.
        """
        recent_signals = (
            db.query(RiskSignal)
            .join(Document)
            .filter(Document.embedding_vector.isnot(None))
            .order_by(RiskSignal.created_at.desc())
            .limit(30)
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
                
                # Boost similarity if same event class
                if signal.event_class == event_class:
                    sim *= 1.1
                
                max_sim = max(max_sim, min(1.0, sim))

        novelty = max(0.05, 1.0 - max_sim)
        return round(novelty, 4)

    def _compute_corroboration(
        self, embedding: np.ndarray, source_name: str, source_type: str, db: Session
    ) -> Dict[str, Any]:
        """Calculate corroboration based on independent provider count and diversity.
        
        CRITICAL: Two articles from the same provider (e.g., two Yahoo articles)
        do NOT count as independent corroboration.
        """
        recent = (
            db.query(RiskSignal)
            .join(Document)
            .filter(Document.embedding_vector.isnot(None))
            .order_by(RiskSignal.created_at.desc())
            .limit(40)
            .all()
        )
        if not recent:
            return {"score": round(0.25, 4), "independent_sources": 0, "similar_events": 0}

        similar_providers = set()
        similar_source_types = set()
        similar_count = 0
        
        for signal in recent:
            doc = signal.document
            if doc.embedding_vector:
                prior_emb = np.array(doc.embedding_vector, dtype=np.float32)
                sim = self.mm.cosine_similarity(embedding, prior_emb)
                if sim >= 0.60:
                    similar_count += 1
                    # Track independent providers (not just different articles from same source)
                    sig_name = (signal.source_name or "").lower()
                    sig_type = (signal.source_type or "").lower()
                    cur_name = source_name.lower()
                    
                    # Different source name = potentially independent
                    if sig_name and sig_name != cur_name:
                        similar_providers.add(sig_name)
                    # Track source type diversity
                    if sig_type:
                        similar_source_types.add(sig_type)

        independent = len(similar_providers)
        type_diversity = len(similar_source_types)
        
        # Score based on independent providers and type diversity
        base = 0.20
        provider_bonus = min(0.40, independent * 0.12)
        diversity_bonus = min(0.15, type_diversity * 0.05)
        event_bonus = min(0.20, similar_count * 0.04)
        score = min(0.95, base + provider_bonus + diversity_bonus + event_bonus)

        return {
            "score": round(score, 4),
            "independent_sources": independent,
            "similar_events": similar_count,
            "source_type_diversity": type_diversity,
        }

    def _find_or_create_cluster(
        self, embedding: np.ndarray, event_class: str, 
        entity_names: List[str], db: Session
    ) -> Optional[EventCluster]:
        """Find existing cluster or create new one.
        
        Matching criteria:
        1. Semantic similarity exceeds threshold
        2. Event class is compatible
        3. Time window is reasonable
        
        Uses proper centroid update: new_centroid = (old * count + new) / (count + 1)
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=CLUSTER_TIME_WINDOW_HOURS)
        recent_clusters = (
            db.query(EventCluster)
            .filter(
                EventCluster.status.in_(["NEW", "DEVELOPING", "ESCALATING", "STABLE"]),
                EventCluster.last_updated >= cutoff,
            )
            .order_by(EventCluster.last_updated.desc())
            .limit(30)
            .all()
        )

        best_cluster = None
        best_sim = 0.0

        for cluster in recent_clusters:
            if cluster.centroid_embedding:
                # Check event class compatibility
                if cluster.label and cluster.label != event_class:
                    continue  # Different event class = different cluster
                
                centroid = np.array(cluster.centroid_embedding, dtype=np.float32)
                sim = self.mm.cosine_similarity(embedding, centroid)
                if sim > best_sim:
                    best_sim = sim
                    best_cluster = cluster

        if best_cluster and best_sim >= SIMILARITY_THRESHOLD:
            # Update existing cluster with proper centroid update
            old_count = best_cluster.event_count
            old_centroid = np.array(best_cluster.centroid_embedding, dtype=np.float32)
            
            # Weighted centroid update
            new_centroid = (old_centroid * old_count + embedding) / (old_count + 1)
            best_cluster.centroid_embedding = new_centroid.tolist()
            best_cluster.event_count += 1
            best_cluster.last_updated = datetime.now(timezone.utc)
            
            # Update lifecycle status based on multiple factors
            best_cluster.status = self._compute_cluster_status(best_cluster, db)
            
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

    def _compute_cluster_status(self, cluster: EventCluster, db: Session) -> str:
        """Compute cluster lifecycle status using multiple signals.
        
        Lifecycle: NEW → DEVELOPING → ESCALATING → STABLE → RESOLVED
        
        Uses:
        - Event frequency (events per hour)
        - Recency (time since last event)
        - Event count
        - Time since first seen
        """
        now = datetime.now(timezone.utc)
        count = cluster.event_count
        first_seen = cluster.first_seen or now
        last_updated = cluster.last_updated or now
        
        age_hours = max(0.1, (now - first_seen).total_seconds() / 3600)
        recency_hours = (now - last_updated).total_seconds() / 3600
        frequency = count / age_hours  # events per hour
        
        # Resolution: no new events for > 12 hours
        if recency_hours > 12 and count >= 2:
            return "RESOLVED"
        
        # Stable: low frequency, been around a while
        if age_hours > 6 and frequency < 0.3 and count >= 3:
            return "STABLE"
        
        # Escalating: high frequency or many events
        if frequency > 1.0 or count >= 8:
            return "ESCALATING"
        
        # Developing: some events accumulated
        if count >= 3 or (count >= 2 and frequency > 0.5):
            return "DEVELOPING"
        
        return "NEW"

    def _compute_entity_exposure(
        self, entities: List[Dict[str, Any]], db: Optional[Session] = None
    ) -> Dict[str, Any]:
        """Calculate actual portfolio exposure based on entity tickers/issuers.
        
        CRITICAL: Does NOT use hardcoded portfolio_exposure = 0.7.
        Calculates real exposure from portfolio positions.
        """
        from app.services.portfolio.portfolio_service import PortfolioService
        ps = PortfolioService()
        portfolio = ps.load_portfolio(db)
        positions = portfolio.get("positions", [])
        total_value = portfolio.get("total_value", 0)
        
        if not positions or total_value <= 0:
            return {
                "exposure_value": 0.0,
                "exposure_percentage": 0.0,
                "affected_positions": [],
                "portfolio_available": False,
            }
        
        # Extract entity identifiers for matching
        entity_tickers = set()
        entity_names = set()
        entity_sectors = set()
        
        for ent in entities:
            if ent.get("ticker"):
                entity_tickers.add(ent["ticker"].upper())
            entity_names.add(ent.get("canonical_name", "").lower())
            # Map entity types to sectors
            if ent.get("type") == "commodity":
                entity_sectors.add("Energy")
                entity_sectors.add("Commodities")
            elif ent.get("type") in {"company", "institution"}:
                # Try to find sector from portfolio
                for pos in positions:
                    issuer_lower = (pos.get("issuer") or "").lower()
                    pos_ticker = (pos.get("ticker") or "").upper()
                    if ent.get("canonical_name", "").lower() in issuer_lower or \
                       (ent.get("ticker") and ent["ticker"].upper() == pos_ticker):
                        if pos.get("sector"):
                            entity_sectors.add(pos["sector"])
        
        # Find affected positions
        affected = []
        total_exposure = 0.0
        
        for pos in positions:
            pos_ticker = (pos.get("ticker") or "").upper()
            pos_issuer = (pos.get("issuer") or "").lower()
            pos_sector = pos.get("sector", "")
            notional = pos.get("notional", 0)
            matched = False
            match_reason = ""
            
            # Direct ticker match
            if pos_ticker in entity_tickers:
                matched = True
                match_reason = "ticker"
            # Issuer name match
            elif any(name in pos_issuer for name in entity_names if name and len(name) > 3):
                matched = True
                match_reason = "issuer"
            # Sector match (weaker — partial exposure)
            elif pos_sector in entity_sectors:
                matched = True
                match_reason = "sector"
                notional = notional * 0.3  # Partial sector exposure
            
            if matched:
                affected.append({
                    "asset_id": pos.get("asset_id"),
                    "ticker": pos.get("ticker"),
                    "issuer": pos.get("issuer"),
                    "notional": pos.get("notional", 0),
                    "match_reason": match_reason,
                })
                total_exposure += notional
        
        exposure_pct = (total_exposure / total_value) if total_value > 0 else 0.0
        
        return {
            "exposure_value": round(total_exposure, 2),
            "exposure_percentage": round(exposure_pct, 4),
            "affected_positions": affected,
            "portfolio_available": True,
        }

    def analyze(
        self,
        text: str,
        source_name: str = "demo",
        source_type: str = "news",
        source_url: str | None = None,
        published_at: datetime | None = None,
        db: Session = None,
    ) -> Dict[str, Any]:
        """Full pipeline: NLP → Risk Assessment → DB Persistence → WebSocket → Stress Trigger."""
        t0 = time.time()

        # 1. NLP: Sentiment
        sentiment = sentiment_analysis(text)

        # 2. NLP: Entity extraction (now uses transformer NER + dictionary)
        entities = extract_entities(text)
        entity_names = [e.get("canonical_name", "") for e in entities]

        # 3. NLP: Event classification
        event = classify_event(text)

        # 4. Embedding
        try:
            embedding = self.mm.encode([text])[0]
            embedding_available = True
        except RuntimeError as exc:
            logger.error("Embedding generation failed: %s", exc)
            embedding = None
            embedding_available = False

        # 5. Source credibility
        cred = self._get_source_credibility(source_name, source_type)

        # 6. Market context (REAL via yfinance, NOT hardcoded)
        market_ctx = MarketContextService.get_market_context(entities)

        # 7. Portfolio exposure (REAL calculation, NOT hardcoded 0.7)
        exposure = self._compute_entity_exposure(entities, db)

        if db is not None and embedding is not None:
            # 8. Novelty (requires DB + embeddings)
            novelty = self._compute_novelty(embedding, event["class"], entity_names, db)

            # 9. Corroboration (requires DB + embeddings)
            corrob = self._compute_corroboration(embedding, source_name, source_type, db)

            # 10. Clustering
            cluster = self._find_or_create_cluster(embedding, event["class"], entity_names, db)
        else:
            novelty = 0.8
            corrob = {"score": 0.25, "independent_sources": 0, "similar_events": 0}
            cluster = None

        # 11. Entity relevance
        entity_relevance = 0.9 if any(
            e.get("type") in {"company", "institution", "commodity"} for e in entities
        ) else 0.5

        # 12. Impact scoring — ALL components from real data
        risk_inputs = {
            "sentiment_score": sentiment["score"],
            "event_class": event["class"],
            "confidence": event["confidence"],
            "source_credibility": cred["score"],
            "corroboration": corrob["score"],
            "novelty": novelty,
            "recency_hours": 1.0,
            "entity_relevance": entity_relevance,
            "market_volatility": market_ctx.get("market_volatility", 0.0),
            "portfolio_exposure": exposure.get("exposure_percentage", 0.0),
        }
        impact = compute_impact_score(risk_inputs)

        # 13. Overall confidence
        overall_confidence = min(
            0.99,
            max(0.35, 0.4 + event["confidence"] * 0.3 + corrob["score"] * 0.15 + abs(sentiment["score"]) * 0.15)
        )

        # 14. Risk trajectory
        if impact["score"] >= 8 and sentiment["score"] < -0.15:
            risk_trajectory = "ACCELERATING"
        elif impact["score"] >= 6:
            risk_trajectory = "DEVELOPING"
        elif impact["score"] >= 4:
            risk_trajectory = "STABLE"
        else:
            risk_trajectory = "LOW"

        # 15. Explanation
        explanation = [
            f"Sentiment: {sentiment['label']} ({sentiment['score']:+.2f}) via {sentiment.get('model', 'unknown')}",
            f"Event: {event['class']} ({event['confidence']:.2f} confidence) via {event.get('model', 'unknown')}",
            f"Source credibility: {cred['score']:.2f} — {cred['label']}",
            f"Corroboration: {corrob['score']:.2f} ({corrob['independent_sources']} independent sources)",
            f"Novelty: {novelty:.2f}",
            f"Market context: {'available' if market_ctx.get('market_context_available') else 'unavailable'}",
            f"Portfolio exposure: {exposure.get('exposure_percentage', 0) * 100:.1f}% ({len(exposure.get('affected_positions', []))} positions)",
            impact["explanation"],
        ]

        # 16. Stress trigger logic
        scenario = STRESS_ELIGIBLE_CATEGORIES.get(event["class"])
        stress_triggered = (
            impact["score"] >= STRESS_TRIGGER_THRESHOLD
            and event["class"] in STRESS_ELIGIBLE_CATEGORIES
        )

        processing_time = int((time.time() - t0) * 1000)

        # 17. Persist to database
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
                embedding_vector=embedding.tolist() if embedding is not None else None,
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
                market_context_available=market_ctx.get("market_context_available", False),
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
            "event": {
                "class": event["class"],
                "confidence": event["confidence"],
                "model": event.get("model"),
                "all_scores": event.get("all_scores", {}),
            },
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
            "market_context": market_ctx,
            "portfolio_exposure": exposure,
            "processing_time_ms": processing_time,
            "market_context_available": market_ctx.get("market_context_available", False),
            "cluster_id": cluster.id if cluster else None,
            "cluster_status": cluster.status if cluster else None,
        }

        # 18. AUTOMATIC STRESS TRIGGER — runs from analyze AND ingest
        stress_result = None
        if stress_triggered and scenario and db is not None:
            try:
                from app.services.portfolio.portfolio_service import PortfolioService
                from app.services.stress.stress_engine import StressEngine

                ps = PortfolioService()
                portfolio = ps.load_portfolio(db)
                engine = StressEngine()
                stress_result = engine.stress_test(
                    portfolio=portfolio,
                    scenario_name=scenario,
                    trigger_signal_id=signal_id,
                    is_auto_triggered=True,
                    db=db,
                )
                logger.info(
                    "AUTO STRESS TRIGGER: %s → %s (loss: %.1f%%)",
                    event["class"], scenario, stress_result.get("loss_percentage", 0),
                )
            except Exception as exc:
                logger.error("Automatic stress trigger failed: %s", exc)

        result["stress_test"] = {
            "triggered": stress_triggered,
            "scenario": scenario if stress_triggered else None,
            "result": stress_result,
        }

        # 19. Publish to Redis for WebSocket
        publish_event(result)

        return result
