"""
Risk Fusion Service — Core pipeline that transforms financial text
through the complete NLP + risk assessment pipeline.

Pipeline:
1. Model Availability Preflight (fails cleanly with HTTP 503 / ModelUnavailableError)
2. Duplicate Protection (deterministic content / URL matching)
3. Sentiment Analysis (FinBERT)
4. Entity Extraction & Resolution (Transformer NER + Canonical mapping)
5. Event Classification (Zero-shot into canonical taxonomy with 'Other' threshold)
6. Embedding Generation (all-MiniLM-L6-v2)
7. Entity-aware Novelty Computation
8. Provider-based Independent Corroboration
9. Multi-factor Event Clustering (semantic + class + entity overlap + time window)
10. Dynamic Market Context (yfinance with benchmark fallback)
11. Transparent Portfolio Exposure (separate direct vs. indirect sector heuristic)
12. Real Recency (timezone-aware delta from published_at)
13. Explainable Impact Scoring (no fabricated defaults, clamped 1-10)
14. Database Persistence (PostgreSQL / SQLAlchemy)
15. Automatic Stress Testing Trigger (strictly for eligible categories)
16. Redis Event Publication for WebSocket broadcast
"""
from __future__ import annotations

import hashlib
import logging
import os
import time
import urllib.parse
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np
from sqlalchemy.orm import Session

from app.core.model_manager import (
    get_model_manager,
    ModelUnavailableError,
    READY,
)
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

# Source credibility profiles — prototype expert assumptions
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
CLUSTER_SIMILARITY_THRESHOLD = 0.75
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


def normalize_source_metadata(
    source_name: str, source_type: str, source_url: Optional[str]
) -> Dict[str, str]:
    """Extract normalized provider and domain metadata for independent corroboration."""
    name_clean = (source_name or "unknown").strip()
    type_clean = (source_type or "news").strip().lower()
    domain = ""

    if source_url:
        try:
            parsed = urllib.parse.urlparse(source_url)
            netloc = parsed.netloc.lower()
            if netloc.startswith("www."):
                netloc = netloc[4:]
            domain = netloc
        except Exception:
            domain = ""

    # Normalize provider identity
    name_lower = name_clean.lower()
    if "yahoo" in domain or "yahoo" in name_lower:
        provider = "Yahoo Finance"
        if not domain:
            domain = "finance.yahoo.com"
    elif "reuters" in domain or "reuters" in name_lower:
        provider = "Reuters"
        if not domain:
            domain = "reuters.com"
    elif "bloomberg" in domain or "bloomberg" in name_lower:
        provider = "Bloomberg"
        if not domain:
            domain = "bloomberg.com"
    elif "sec.gov" in domain or "sec" in name_lower:
        provider = "SEC"
        if not domain:
            domain = "sec.gov"
    elif "federalreserve" in domain or "fed" in name_lower or "central bank" in name_lower:
        provider = "Federal Reserve"
        if not domain:
            domain = "federalreserve.gov"
    elif type_clean == "dataset":
        provider = f"Dataset: {name_clean}"
        domain = "huggingface.co"
    elif type_clean == "demo":
        provider = "Synthetic Demo"
        domain = "localhost"
    else:
        provider = domain if domain else name_clean

    return {
        "provider": provider,
        "domain": domain,
        "source_type": type_clean,
        "source_url": source_url or "",
    }


class MarketContextService:
    """Fetch real market data via yfinance. Cached to avoid excessive API calls."""

    _cache: Dict[str, Dict[str, Any]] = {}
    _cache_ttl: timedelta = timedelta(minutes=15)
    _failure_cooldowns: Dict[str, datetime] = {}
    _cooldown_ttl: timedelta = timedelta(seconds=60)
    _provider_cooldown_until: Optional[datetime] = None
    _bypass_in_tests: bool = True

    @classmethod
    def clear_cache(cls) -> None:
        """Clear memory cache and cooldown state (primarily for tests)."""
        cls._cache.clear()
        cls._failure_cooldowns.clear()
        cls._provider_cooldown_until = None

    @classmethod
    def _is_rate_limit_error(cls, exc: Exception) -> bool:
        """Check if an exception indicates a rate-limit / 429 response."""
        name = type(exc).__name__.lower()
        msg = str(exc).lower()
        return (
            "ratelimit" in name
            or "rate limited" in msg
            or "too many requests" in msg
            or "429" in msg
        )

    @classmethod
    def _record_failure(cls, ticker: str, exc: Exception) -> None:
        """Record a failure and activate cooldown."""
        now_utc = datetime.now(timezone.utc)
        cls._failure_cooldowns[ticker] = now_utc + cls._cooldown_ttl
        logger.warning("yfinance fetch failed for %s: %s", ticker, exc)

        if cls._is_rate_limit_error(exc):
            cls._provider_cooldown_until = now_utc + cls._cooldown_ttl
            logger.info(
                "yfinance rate-limit detected for %s; provider cooldown active for %ds",
                ticker,
                int(cls._cooldown_ttl.total_seconds()),
            )

    @classmethod
    def get_market_context(cls, entities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get market volatility for relevant entities or market benchmark."""
        tickers = []
        for ent in entities:
            ticker = ent.get("ticker")
            if ticker and ent.get("type") in {"company", "institution", "commodity"}:
                tickers.append(ticker)

        if not tickers:
            tickers = ["SPY"]

        if os.getenv("TESTING") == "1" and cls._bypass_in_tests:
            return {
                "market_context_available": False,
                "market_volatility": 0.0,
                "note": "Testing environment — external market data bypassed",
            }

        try:
            import yfinance as yf

            volatilities = []
            price_changes = []

            for ticker in tickers[:3]:
                cache_key = ticker
                now_utc = datetime.now(timezone.utc)

                # 1. Check success cache
                if cache_key in cls._cache:
                    cached = cls._cache[cache_key]
                    if now_utc - cached["fetched_at"] < cls._cache_ttl:
                        volatilities.append(cached.get("volatility", 0.0))
                        price_changes.append(cached.get("price_change", 0.0))
                        continue
                    else:
                        cls._cache.pop(cache_key, None)

                # 2. Check provider-wide rate-limit cooldown
                if cls._provider_cooldown_until:
                    if now_utc < cls._provider_cooldown_until:
                        logger.debug("Skipping yfinance fetch for %s — provider cooldown active", ticker)
                        continue
                    else:
                        cls._provider_cooldown_until = None

                # 3. Check ticker-specific failure cooldown
                if ticker in cls._failure_cooldowns:
                    cooldown_until = cls._failure_cooldowns[ticker]
                    if now_utc < cooldown_until:
                        logger.debug("Skipping yfinance fetch for %s — ticker cooldown active", ticker)
                        continue
                    else:
                        cls._failure_cooldowns.pop(ticker, None)

                # 4. Attempt fetch with short timeout to fail fast
                try:
                    stock = yf.Ticker(ticker)
                    hist = stock.history(period="1mo", timeout=5)
                    if hist.empty or len(hist) < 5:
                        cls._failure_cooldowns[ticker] = now_utc + cls._cooldown_ttl
                        continue

                    returns = hist["Close"].pct_change().dropna()
                    vol = float(returns.std() * (252 ** 0.5))
                    price_change = float((hist["Close"].iloc[-1] / hist["Close"].iloc[-5] - 1))

                    volatilities.append(vol)
                    price_changes.append(price_change)

                    cls._cache[cache_key] = {
                        "volatility": vol,
                        "price_change": price_change,
                        "fetched_at": now_utc,
                    }
                    cls._failure_cooldowns.pop(ticker, None)
                except Exception as exc:
                    cls._record_failure(ticker, exc)
                    continue

            if volatilities:
                avg_vol = sum(volatilities) / len(volatilities)
                avg_change = sum(price_changes) / len(price_changes)
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
            "note": "Market data unavailable — impact score component scored at 0.0",
        }


class RiskFusionService:
    """Stateless risk fusion engine — persists signals, clusters, and stress results."""

    def __init__(self) -> None:
        self.mm = get_model_manager()

    def _get_source_credibility(self, source_name: str, source_type: str) -> Dict[str, Any]:
        key = (source_type or "").lower()
        name_lower = (source_name or "").lower()

        if any(kw in name_lower for kw in ["fed", "central bank", "regulator", "sec"]):
            profile = SOURCE_CREDIBILITY["official_regulator"]
        elif any(kw in name_lower for kw in ["yahoo", "reuters", "bloomberg"]):
            profile = SOURCE_CREDIBILITY["major_financial_news"]
        elif key in SOURCE_CREDIBILITY:
            profile = SOURCE_CREDIBILITY[key]
        else:
            profile = SOURCE_CREDIBILITY.get("general_news", {"score": 0.68, "label": "General News"})

        return {
            "score": profile["score"],
            "label": profile["label"],
            "note": "Prototype source credibility assumption",
        }

    def _compute_novelty(
        self,
        embedding: np.ndarray,
        event_class: str,
        entity_names: List[str],
        db: Session,
    ) -> float:
        """Calculate novelty considering semantic similarity, event class, and entity overlap.

        An event is novel if:
        - It covers different entities, even if the text looks like another earnings/launch event.
        - Or if its semantic similarity with recent events of the same class is low.
        """
        recent_signals = (
            db.query(RiskSignal)
            .join(Document)
            .filter(Document.embedding_vector.isnot(None))
            .order_by(RiskSignal.created_at.desc())
            .limit(40)
            .all()
        )
        if not recent_signals:
            return 0.85

        now_utc = datetime.now(timezone.utc)
        cur_entity_set = {n.lower().strip() for n in entity_names if n.strip()}
        max_overlap_similarity = 0.0

        for signal in recent_signals:
            doc = signal.document
            if not doc.embedding_vector:
                continue

            prior_emb = np.array(doc.embedding_vector, dtype=np.float32)
            sem_sim = self.mm.cosine_similarity(embedding, prior_emb)

            # Class compatibility factor
            class_match = 1.0 if signal.event_class == event_class else 0.4

            # Entity overlap factor
            prior_entities = set()
            if doc.document_entities:
                for de in doc.document_entities:
                    if de.entity and de.entity.canonical_name:
                        prior_entities.add(de.entity.canonical_name.lower().strip())

            if cur_entity_set and prior_entities:
                overlap = len(cur_entity_set & prior_entities) / len(cur_entity_set | prior_entities)
            elif not cur_entity_set and not prior_entities:
                overlap = 0.4
            else:
                overlap = 0.1

            # Time decay over 72 hours
            sig_created = signal.created_at or now_utc
            if sig_created.tzinfo is None:
                sig_created = sig_created.replace(tzinfo=timezone.utc)
            age_hours = max(0.0, (now_utc - sig_created).total_seconds() / 3600.0)
            time_decay = max(0.2, 1.0 - (age_hours / 72.0))

            combined_prior_match = (
                0.50 * sem_sim + 0.30 * overlap + 0.20 * class_match
            ) * time_decay

            max_overlap_similarity = max(max_overlap_similarity, combined_prior_match)

        novelty = round(max(0.05, min(1.0, 1.0 - max_overlap_similarity)), 4)
        return novelty

    def _compute_corroboration(
        self,
        embedding: np.ndarray,
        source_name: str,
        source_type: str,
        source_url: Optional[str],
        db: Session,
    ) -> Dict[str, Any]:
        """Calculate corroboration based on independent provider and domain count.

        Multiple articles from the same provider (e.g., Yahoo Finance AAPL and Yahoo Finance MSFT)
        count as ONE provider and do not artificially inflate independent corroboration.
        """
        recent = (
            db.query(RiskSignal)
            .join(Document)
            .filter(Document.embedding_vector.isnot(None))
            .order_by(RiskSignal.created_at.desc())
            .limit(50)
            .all()
        )

        current_meta = normalize_source_metadata(source_name, source_type, source_url)
        cur_provider = current_meta["provider"]
        cur_domain = current_meta["domain"]

        if not recent:
            return {
                "score": 0.20,
                "independent_sources": 0,
                "independent_provider_count": 0,
                "independent_domains": [],
                "similar_event_count": 0,
                "source_type_diversity": 1,
                "corroboration_score": 0.20,
            }

        independent_providers: Set[str] = set()
        independent_domains: Set[str] = set()
        similar_source_types: Set[str] = {current_meta["source_type"]}
        similar_count = 0

        for signal in recent:
            doc = signal.document
            if not doc.embedding_vector:
                continue

            prior_emb = np.array(doc.embedding_vector, dtype=np.float32)
            sim = self.mm.cosine_similarity(embedding, prior_emb)

            if sim >= 0.60:
                similar_count += 1
                prior_meta = normalize_source_metadata(
                    signal.source_name or "", signal.source_type or "", doc.source_url
                )

                if prior_meta["provider"] and prior_meta["provider"] != cur_provider:
                    independent_providers.add(prior_meta["provider"])
                if prior_meta["domain"] and prior_meta["domain"] != cur_domain:
                    independent_domains.add(prior_meta["domain"])
                if prior_meta["source_type"]:
                    similar_source_types.add(prior_meta["source_type"])

        ind_provider_count = len(independent_providers)
        type_diversity = len(similar_source_types)

        base = 0.20
        provider_bonus = min(0.40, ind_provider_count * 0.12)
        diversity_bonus = min(0.15, type_diversity * 0.05)
        event_bonus = min(0.20, similar_count * 0.04)
        corroboration_score = round(min(0.95, base + provider_bonus + diversity_bonus + event_bonus), 4)

        return {
            "score": corroboration_score,
            "independent_sources": ind_provider_count,
            "independent_provider_count": ind_provider_count,
            "independent_domains": sorted(list(independent_domains)),
            "similar_event_count": similar_count,
            "source_type_diversity": type_diversity,
            "corroboration_score": corroboration_score,
        }

    def _find_or_create_cluster(
        self,
        embedding: np.ndarray,
        event_class: str,
        entity_names: List[str],
        text: str,
        db: Session,
    ) -> Optional[EventCluster]:
        """Find existing cluster or create new one using multi-factor criteria.

        Criteria:
        1. Semantic similarity exceeds threshold
        2. Event class must be compatible
        3. Entity overlap check: distinct corporate entities (e.g. Apple vs Tesla)
           must not be merged into the same event cluster.
        4. Time window is strictly within CLUSTER_TIME_WINDOW_HOURS.
        """
        now_utc = datetime.now(timezone.utc)
        cutoff = now_utc - timedelta(hours=CLUSTER_TIME_WINDOW_HOURS)

        recent_clusters = (
            db.query(EventCluster)
            .filter(
                EventCluster.status.in_(["NEW", "DEVELOPING", "ESCALATING", "STABLE", "RESOLVING"]),
                EventCluster.last_updated >= cutoff,
            )
            .order_by(EventCluster.last_updated.desc())
            .limit(30)
            .all()
        )

        cur_entity_set = {n.lower().strip() for n in entity_names if n.strip()}
        best_cluster = None
        best_score = 0.0

        for cluster in recent_clusters:
            if not cluster.centroid_embedding:
                continue

            # 1. Event class compatibility
            if cluster.label and cluster.label != event_class:
                continue

            centroid = np.array(cluster.centroid_embedding, dtype=np.float32)
            sem_sim = self.mm.cosine_similarity(embedding, centroid)
            if sem_sim < 0.65:
                continue

            # 2. Entity overlap check
            cluster_entities: Set[str] = set()
            for sig in cluster.risk_signals:
                if sig.document and sig.document.document_entities:
                    for de in sig.document.document_entities:
                        if de.entity and de.entity.canonical_name:
                            cluster_entities.add(de.entity.canonical_name.lower().strip())

            # For company-specific events, prevent clustering different companies
            is_company_specific = event_class in {
                "Earnings", "Product Launch", "Merger & Acquisition",
                "Management / Leadership", "Corporate Action",
            }
            if is_company_specific and cur_entity_set and cluster_entities:
                overlap = len(cur_entity_set & cluster_entities) / len(cur_entity_set | cluster_entities)
                if overlap < 0.2:
                    continue  # Different companies, cannot belong to the same cluster
            elif cur_entity_set and cluster_entities:
                overlap = len(cur_entity_set & cluster_entities) / len(cur_entity_set | cluster_entities)
            else:
                overlap = 0.5

            match_score = 0.70 * sem_sim + 0.30 * overlap
            if match_score > best_score:
                best_score = match_score
                best_cluster = cluster

        if best_cluster and best_score >= CLUSTER_SIMILARITY_THRESHOLD:
            # Weighted centroid update
            old_count = best_cluster.event_count or 1
            old_centroid = np.array(best_cluster.centroid_embedding, dtype=np.float32)
            new_centroid = (old_centroid * old_count + embedding) / (old_count + 1)

            best_cluster.centroid_embedding = new_centroid.tolist()
            best_cluster.event_count = old_count + 1
            best_cluster.last_updated = now_utc
            if not best_cluster.representative_text:
                best_cluster.representative_text = text[:300]
            best_cluster.status = self._compute_cluster_status(best_cluster)
            return best_cluster

        # Create new cluster
        cluster = EventCluster(
            id=str(uuid.uuid4()),
            label=event_class,
            representative_text=text[:300],
            status="NEW",
            event_count=1,
            first_seen=now_utc,
            last_updated=now_utc,
            centroid_embedding=embedding.tolist(),
        )
        db.add(cluster)
        return cluster

    def _compute_cluster_status(self, cluster: EventCluster) -> str:
        """Compute cluster lifecycle status: NEW, DEVELOPING, ESCALATING, STABLE, RESOLVING, RESOLVED."""
        now_utc = datetime.now(timezone.utc)
        count = cluster.event_count or 1
        first_seen = cluster.first_seen or now_utc
        last_updated = cluster.last_updated or now_utc

        if first_seen.tzinfo is None:
            first_seen = first_seen.replace(tzinfo=timezone.utc)
        if last_updated.tzinfo is None:
            last_updated = last_updated.replace(tzinfo=timezone.utc)

        age_hours = max(0.1, (now_utc - first_seen).total_seconds() / 3600.0)
        recency_hours = max(0.0, (now_utc - last_updated).total_seconds() / 3600.0)
        frequency = count / age_hours

        if count <= 1:
            return "NEW"

        # Multi-factor resolution: quiet for > 24h with multiple events, or very long inactive
        if recency_hours > 24.0 and count >= 2:
            return "RESOLVED"
        if recency_hours > 12.0 and count >= 3 and frequency < 0.2:
            return "RESOLVING"
        if frequency > 1.0 or count >= 8:
            return "ESCALATING"
        if count >= 3 or (count >= 2 and frequency > 0.4):
            return "DEVELOPING"
        if age_hours > 8.0 and frequency < 0.3 and count >= 3:
            return "STABLE"

        return "NEW"

    def _compute_entity_exposure(
        self, entities: List[Dict[str, Any]], db: Optional[Session] = None
    ) -> Dict[str, Any]:
        """Calculate actual portfolio exposure with clear separation of direct and indirect exposure.

        Does NOT double-count positions.
        Indirect sector exposure is transparently calculated at 30% notional heuristic.
        """
        from app.services.portfolio.portfolio_service import PortfolioService
        ps = PortfolioService()
        portfolio = ps.load_portfolio(db)
        positions = portfolio.get("positions", [])
        total_value = float(portfolio.get("total_value", 0.0))

        if not positions or total_value <= 0:
            return {
                "direct_exposure_value": 0.0,
                "direct_exposure_percentage": 0.0,
                "indirect_sector_exposure_value": 0.0,
                "indirect_sector_exposure_percentage": 0.0,
                "total_exposure_value": 0.0,
                "total_exposure_percentage": 0.0,
                "affected_positions": [],
                "portfolio_available": False,
                "heuristic_label": "Portfolio data unavailable",
            }

        if not entities:
            return {
                "direct_exposure_value": 0.0,
                "direct_exposure_percentage": 0.0,
                "indirect_sector_exposure_value": 0.0,
                "indirect_sector_exposure_percentage": 0.0,
                "total_exposure_value": 0.0,
                "total_exposure_percentage": 0.0,
                "affected_positions": [],
                "portfolio_available": True,
                "heuristic_label": "No identifiable entities in event text; zero direct exposure calculated.",
            }

        entity_tickers = {e["ticker"].upper() for e in entities if e.get("ticker")}
        entity_names = {e.get("canonical_name", "").lower() for e in entities if e.get("canonical_name")}
        entity_sectors: Set[str] = set()

        for ent in entities:
            if ent.get("type") == "commodity":
                entity_sectors.add("Energy")
                entity_sectors.add("Commodities")
            elif ent.get("type") in {"company", "institution"}:
                for pos in positions:
                    issuer_lower = (pos.get("issuer") or "").lower()
                    pos_ticker = (pos.get("ticker") or "").upper()
                    if (
                        ent.get("canonical_name", "").lower() in issuer_lower
                        or (ent.get("ticker") and ent["ticker"].upper() == pos_ticker)
                    ):
                        if pos.get("sector"):
                            entity_sectors.add(pos["sector"])

        affected_positions = []
        direct_exposure_val = 0.0
        indirect_exposure_val = 0.0
        seen_asset_ids: Set[str] = set()

        # Pass 1: Direct matches (ticker or issuer)
        for pos in positions:
            aid = pos.get("asset_id", "")
            pos_ticker = (pos.get("ticker") or "").upper()
            pos_issuer = (pos.get("issuer") or "").lower()
            notional = float(pos.get("notional", 0.0))

            is_direct = False
            match_reason = ""

            if pos_ticker and pos_ticker in entity_tickers:
                is_direct = True
                match_reason = "direct_ticker"
            elif any(name in pos_issuer for name in entity_names if len(name) > 3):
                is_direct = True
                match_reason = "direct_issuer"

            if is_direct:
                seen_asset_ids.add(aid)
                direct_exposure_val += notional
                affected_positions.append({
                    "asset_id": aid,
                    "ticker": pos.get("ticker"),
                    "issuer": pos.get("issuer"),
                    "notional": notional,
                    "exposure_type": "direct",
                    "effective_exposure": notional,
                    "match_reason": match_reason,
                })

        # Pass 2: Indirect sector matches (non-double-counted)
        for pos in positions:
            aid = pos.get("asset_id", "")
            if aid in seen_asset_ids:
                continue  # Already counted as direct!

            pos_sector = pos.get("sector", "")
            notional = float(pos.get("notional", 0.0))

            if pos_sector and pos_sector in entity_sectors:
                seen_asset_ids.add(aid)
                # Transparent heuristic: 30% sector spillover
                effective_notional = notional * 0.30
                indirect_exposure_val += effective_notional
                affected_positions.append({
                    "asset_id": aid,
                    "ticker": pos.get("ticker"),
                    "issuer": pos.get("issuer"),
                    "notional": notional,
                    "exposure_type": "indirect_sector",
                    "effective_exposure": round(effective_notional, 2),
                    "match_reason": "sector_heuristic_30pct",
                })

        direct_pct = min(1.0, direct_exposure_val / total_value) if total_value > 0 else 0.0
        indirect_pct = min(1.0, indirect_exposure_val / total_value) if total_value > 0 else 0.0
        total_pct = min(1.0, direct_pct + indirect_pct)

        return {
            "direct_exposure_value": round(direct_exposure_val, 2),
            "direct_exposure_percentage": round(direct_pct, 4),
            "indirect_sector_exposure_value": round(indirect_exposure_val, 2),
            "indirect_sector_exposure_percentage": round(indirect_pct, 4),
            "total_exposure_value": round(direct_exposure_val + indirect_exposure_val, 2),
            "total_exposure_percentage": round(total_pct, 4),
            "affected_positions": affected_positions,
            "portfolio_available": True,
            "heuristic_label": "Direct exposure via ticker/issuer; indirect exposure calculated at 30% sector notional heuristic (non-double-counted).",
        }

    def analyze(
        self,
        text: str,
        source_name: str = "manual",
        source_type: str = "manual",
        source_url: Optional[str] = None,
        published_at: Optional[datetime] = None,
        retrieved_at: Optional[datetime] = None,
        created_at: Optional[datetime] = None,
        db: Optional[Session] = None,
    ) -> Dict[str, Any]:
        """Run complete NLP and risk assessment pipeline.

        CRITICAL:
        - Fails cleanly if mandatory NLP models are unavailable (HTTP 503 / ModelUnavailableError).
        - Prevents duplicate documents and risk signals deterministically.
        - Calculates real recency from published_at, retrieval, or created timestamp;
          explicitly marks recency unavailable if no usable timestamp exists.
        """
        t0 = time.time()
        text_clean = text.strip()
        if not text_clean:
            raise ValueError("Event text cannot be empty.")

        # 1. Preflight: verify mandatory NLP models are ready
        self.mm.check_mandatory_models()

        # 2. Duplicate protection: check if identical text or specific article URL was already ingested
        if db is not None:
            is_generic_dataset_url = source_url in {
                "https://huggingface.co/datasets/twitter_sentiment",
                "https://huggingface.co/datasets/twitter_topic",
                "https://huggingface.co/datasets/financial_phrasebank",
            }
            if source_url and not is_generic_dataset_url:
                doc_query = db.query(Document).filter(
                    (Document.original_text == text_clean)
                    | (Document.source_url == source_url)
                )
            else:
                doc_query = db.query(Document).filter(Document.original_text == text_clean)

            existing_doc = doc_query.first()
            if existing_doc:
                existing_signal = (
                    db.query(RiskSignal)
                    .filter(RiskSignal.document_id == existing_doc.id)
                    .first()
                )
                if existing_signal:
                    logger.info("Deterministic duplicate detected (doc_id=%s). Returning existing signal.", existing_doc.id)
                    from app.api.routes.events import _signal_to_dict
                    res = _signal_to_dict(existing_signal, db=db)
                    res["already_processed"] = True
                    return res

        # 3. NLP: Sentiment Analysis (FinBERT)
        sentiment = sentiment_analysis(text_clean)

        # 4. NLP: Entity Extraction (Transformer NER + Resolution)
        entities = extract_entities(text_clean)
        entity_names = [e["canonical_name"] for e in entities]

        # 5. NLP: Event Classification (Zero-shot MNLI with 'Other' threshold)
        event = classify_event(text_clean)

        # 6. NLP: Sentence Embeddings
        embedding = self.mm.encode([text_clean])[0]

        # 7. Source Credibility & Normalized Metadata
        source_meta = normalize_source_metadata(source_name, source_type, source_url)
        cred = self._get_source_credibility(source_name, source_type)

        # 8. Dynamic Market Context (yfinance with SPY fallback)
        market_ctx = MarketContextService.get_market_context(entities)

        # 9. Portfolio Exposure (direct vs. indirect)
        exposure = self._compute_entity_exposure(entities, db)

        # 10. Real Recency: calculate actual hours from published_at, retrieval, or created timestamp
        now_utc = datetime.now(timezone.utc)
        usable_timestamp = published_at or retrieved_at or created_at
        if usable_timestamp:
            ts = usable_timestamp
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            else:
                ts = ts.astimezone(timezone.utc)
            recency_hours = max(0.0, (now_utc - ts).total_seconds() / 3600.0)
            recency_available = True
        else:
            recency_hours = None
            recency_available = False

        # 11. Novelty & Corroboration & Clustering
        if db is not None:
            novelty = self._compute_novelty(embedding, event["class"], entity_names, db)
            corrob = self._compute_corroboration(
                embedding, source_name, source_type, source_url, db
            )
            cluster = self._find_or_create_cluster(
                embedding, event["class"], entity_names, text_clean, db
            )
        else:
            novelty = 0.80
            corrob = {
                "score": 0.20,
                "independent_sources": 0,
                "independent_provider_count": 0,
                "independent_domains": [],
                "similar_event_count": 0,
                "source_type_diversity": 1,
                "corroboration_score": 0.20,
            }
            cluster = None

        # 12. Entity relevance
        if entities:
            entity_relevance = 0.90 if any(
                e.get("type") in {"company", "institution", "commodity"} for e in entities
            ) else 0.60
        else:
            entity_relevance = 0.30  # Baseline for general news with no specific entity

        # 13. Explainable Impact Scoring (validated inputs, clamped 1-10)
        impact_payload = {
            "sentiment_score": sentiment["score"],
            "event_class": event["class"],
            "confidence": event["confidence"],
            "source_credibility": cred["score"],
            "corroboration": corrob["score"],
            "novelty": novelty,
            "recency_hours": recency_hours,
            "recency_available": recency_available,
            "entity_relevance": entity_relevance,
            "market_volatility": market_ctx.get("market_volatility", 0.0),
            "market_context_available": market_ctx.get("market_context_available", False),
            "portfolio_exposure": exposure.get("total_exposure_percentage", 0.0),
            "portfolio_available": exposure.get("portfolio_available", True),
        }
        impact = compute_impact_score(impact_payload)

        # 14. Overall Confidence & Trajectory
        overall_confidence = round(
            min(
                0.99,
                max(
                    0.35,
                    0.35 + event["confidence"] * 0.30 + corrob["score"] * 0.15 + abs(sentiment["score"]) * 0.20
                )
            ),
            4
        )

        if impact["score"] >= 8.0 and sentiment["score"] < -0.15:
            risk_trajectory = "ACCELERATING"
        elif impact["score"] >= 6.0:
            risk_trajectory = "DEVELOPING"
        elif impact["score"] >= 4.0:
            risk_trajectory = "STABLE"
        else:
            risk_trajectory = "LOW"

        recency_str = (
            f"Recency: {recency_hours:.1f}h ago"
            if (recency_available and recency_hours is not None)
            else "Recency: unavailable"
        )
        explanation = [
            f"Sentiment: {sentiment['label']} ({sentiment['score']:+.2f}) via {sentiment.get('model', 'unknown')}",
            f"Event: {event['class']} ({event['confidence']:.2f} confidence) via {event.get('model', 'unknown')}",
            f"Source credibility: {cred['score']:.2f} — {cred['label']}",
            f"Corroboration: {corrob['score']:.2f} ({corrob.get('independent_provider_count', 0)} independent providers)",
            f"Novelty: {novelty:.2f}",
            recency_str,
            f"Market context: {'available' if market_ctx.get('market_context_available') else 'unavailable'}",
            f"Portfolio exposure: {exposure.get('total_exposure_percentage', 0.0) * 100:.1f}% "
            f"({len(exposure.get('affected_positions', []))} positions: direct ${exposure.get('direct_exposure_value', 0):,.0f}, indirect ${exposure.get('indirect_exposure_value', 0):,.0f})",
            impact["explanation"],
        ]

        # 15. Stress trigger evaluation (strictly for eligible categories)
        scenario = STRESS_ELIGIBLE_CATEGORIES.get(event["class"])
        stress_triggered = (
            impact["score"] >= STRESS_TRIGGER_THRESHOLD
            and event["class"] in STRESS_ELIGIBLE_CATEGORIES
        )

        processing_time = int((time.time() - t0) * 1000)

        # 16. Persistence to PostgreSQL
        signal_id = str(uuid.uuid4())
        doc_id = str(uuid.uuid4())

        if db is not None:
            # Source record
            source_record = db.query(Source).filter(
                Source.name == source_name, Source.source_type == source_type
            ).first()
            if not source_record:
                source_record = Source(
                    id=str(uuid.uuid4()),
                    name=source_name,
                    source_type=source_type,
                    credibility_score=cred["score"],
                    credibility_label=cred["label"],
                    url=source_url,
                )
                db.add(source_record)

            # Document record
            doc = Document(
                id=doc_id,
                source_id=source_record.id,
                original_text=text_clean,
                source_url=source_url,
                published_at=published_at,
                retrieved_at=retrieved_at or now_utc,
                embedding_vector=embedding.tolist(),
            )
            db.add(doc)

            # Entity records
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

            # RiskSignal record
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
                overall_confidence=overall_confidence,
                novelty_score=novelty,
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

        # 17. Execute Automatic Stress Test if triggered
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
                    "AUTOMATIC STRESS TEST TRIGGERED: %s (%s) → %s | Loss: %.2f%% ($%s)",
                    signal_id, event["class"], scenario,
                    stress_result.get("loss_percentage", 0.0),
                    f"{stress_result.get('absolute_loss', 0.0):,.2f}",
                )
            except Exception as exc:
                logger.error("Automatic stress test execution failed: %s", exc)

        # Build response payload
        result = {
            "signal_id": signal_id,
            "document_id": doc_id,
            "timestamp": now_utc.isoformat(),
            "source": {
                "type": source_type,
                "name": source_name,
                "url": source_url,
                "provider": source_meta["provider"],
                "domain": source_meta["domain"],
            },
            "text": text_clean,
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
            "novelty_score": novelty,
            "corroboration": corrob,
            "confidence_score": overall_confidence,
            "risk_trajectory": risk_trajectory,
            "explanation": explanation,
            "market_context": market_ctx,
            "portfolio_exposure": exposure,
            "processing_time_ms": processing_time,
            "market_context_available": market_ctx.get("market_context_available", False),
            "cluster_id": cluster.id if cluster else None,
            "cluster_status": cluster.status if cluster else None,
            "stress_test": {
                "triggered": stress_triggered,
                "scenario": scenario if stress_triggered else None,
                "simulation_id": stress_result.get("simulation_id") if stress_result else None,
                "is_auto_triggered": stress_triggered,
                "result": stress_result,
            },
        }

        # 18. Publish complete payload to Redis for single-subscriber WebSocket broadcast
        publish_payload = {
            "event_id": signal_id,
            "signal_id": signal_id,
            "document_id": doc_id,
            "cluster_id": cluster.id if cluster else None,
            "event_class": event["class"],
            "sentiment": sentiment,
            "impact": impact,
            "risk_level": impact["risk_level"],
            "entities": entities,
            "stress_triggered": stress_triggered,
            "stress_result": stress_result,
            "scenario": scenario if stress_triggered else None,
            "text": text_clean,
            "source": result["source"],
            "timestamp": now_utc.isoformat(),
        }
        publish_event(publish_payload)

        return result
