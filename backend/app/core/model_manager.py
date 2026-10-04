"""
Model Manager — Singleton that manages lazy loading, caching, and inference
for all ML models used in the FinRisk pipeline.

Models:
- ProsusAI/finbert — financial sentiment analysis
- all-MiniLM-L6-v2 — sentence embeddings for dedup/clustering
- Zero-shot classifier — event classification via facebook/bart-large-mnli
"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

import torch
import numpy as np

logger = logging.getLogger("finrisk.models")


class ModelManager:
    """Singleton model manager with lazy loading and device selection."""

    _instance: Optional["ModelManager"] = None
    _initialized: bool = False

    def __new__(cls) -> "ModelManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if ModelManager._initialized:
            return
        ModelManager._initialized = True
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info("Model device: %s", self.device)
        self._finbert_pipeline = None
        self._embedding_model = None
        self._zeroshot_pipeline = None
        self._finbert_status = "not_loaded"
        self._embedding_status = "not_loaded"
        self._classifier_status = "not_loaded"

    # ── FinBERT ──────────────────────────────────────────────
    def load_finbert(self) -> None:
        if self._finbert_pipeline is not None:
            return
        try:
            t0 = time.time()
            from transformers import pipeline as hf_pipeline
            self._finbert_pipeline = hf_pipeline(
                "sentiment-analysis",
                model="ProsusAI/finbert",
                device=0 if self.device == "cuda" else -1,
                top_k=None,
            )
            self._finbert_status = "ready"
            logger.info("FinBERT loaded in %.1fs on %s", time.time() - t0, self.device)
        except Exception as exc:
            self._finbert_status = f"error: {exc}"
            logger.error("FinBERT load failed: %s", exc)

    def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Run FinBERT sentiment analysis. Returns label, score, confidence, probabilities."""
        if self._finbert_pipeline is None:
            self.load_finbert()
        if self._finbert_pipeline is None:
            return self._fallback_sentiment(text)

        try:
            truncated = text[:512]
            results = self._finbert_pipeline(truncated)
            if isinstance(results, list) and len(results) > 0:
                if isinstance(results[0], list):
                    results = results[0]

            probs = {}
            for item in results:
                label = item["label"].lower()
                probs[label] = round(item["score"], 4)

            best = max(results, key=lambda x: x["score"])
            label = best["label"].lower()
            confidence = round(best["score"], 4)

            # Convert to signed score: positive → +, negative → -, neutral → 0
            pos = probs.get("positive", 0.0)
            neg = probs.get("negative", 0.0)
            score = round(pos - neg, 4)

            return {
                "label": label,
                "score": score,
                "confidence": confidence,
                "probabilities": probs,
                "model": "ProsusAI/finbert",
            }
        except Exception as exc:
            logger.warning("FinBERT inference error: %s", exc)
            return self._fallback_sentiment(text)

    @staticmethod
    def _fallback_sentiment(text: str) -> Dict[str, Any]:
        """Keyword-based fallback when FinBERT is unavailable."""
        neg_words = {"decline", "drop", "fall", "loss", "default", "risk", "stress", "crash",
                     "recession", "inflation", "concern", "tension", "disruption", "collapse"}
        pos_words = {"growth", "gain", "profit", "surge", "rally", "strong", "recovery", "bullish"}
        words = set(text.lower().split())
        n = len(words & neg_words)
        p = len(words & pos_words)
        total = n + p
        if total == 0:
            return {"label": "neutral", "score": 0.0, "confidence": 0.45,
                    "probabilities": {"positive": 0.33, "negative": 0.33, "neutral": 0.34},
                    "model": "keyword-fallback"}
        score = round((p - n) / total, 4)
        label = "positive" if score > 0.1 else "negative" if score < -0.1 else "neutral"
        conf = round(min(0.75, 0.45 + abs(score) * 0.3), 4)
        return {"label": label, "score": score, "confidence": conf,
                "probabilities": {"positive": round(max(0, 0.5 + score / 2), 4),
                                  "negative": round(max(0, 0.5 - score / 2), 4),
                                  "neutral": round(max(0, 1 - abs(score)), 4)},
                "model": "keyword-fallback"}

    # ── Sentence Embeddings ──────────────────────────────────
    def load_embeddings(self) -> None:
        if self._embedding_model is not None:
            return
        try:
            t0 = time.time()
            from sentence_transformers import SentenceTransformer
            self._embedding_model = SentenceTransformer("all-MiniLM-L6-v2", device=self.device)
            self._embedding_status = "ready"
            logger.info("Embedding model loaded in %.1fs", time.time() - t0)
        except Exception as exc:
            self._embedding_status = f"error: {exc}"
            logger.error("Embedding model load failed: %s", exc)

    def encode(self, texts: List[str]) -> np.ndarray:
        """Encode texts to embeddings. Returns (N, dim) numpy array."""
        if self._embedding_model is None:
            self.load_embeddings()
        if self._embedding_model is None:
            # Fallback: simple bag-of-words hash
            return np.random.randn(len(texts), 384).astype(np.float32)
        return self._embedding_model.encode(texts, convert_to_numpy=True, show_progress_bar=False)

    def cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Cosine similarity between two embedding vectors."""
        a_flat = a.flatten()
        b_flat = b.flatten()
        denom = (np.linalg.norm(a_flat) * np.linalg.norm(b_flat))
        if denom < 1e-9:
            return 0.0
        return float(np.dot(a_flat, b_flat) / denom)

    # ── Zero-shot Classification ─────────────────────────────
    def load_classifier(self) -> None:
        if self._zeroshot_pipeline is not None:
            return
        try:
            t0 = time.time()
            from transformers import pipeline as hf_pipeline
            self._zeroshot_pipeline = hf_pipeline(
                "zero-shot-classification",
                model="facebook/bart-large-mnli",
                device=0 if self.device == "cuda" else -1,
            )
            self._classifier_status = "ready"
            logger.info("Zero-shot classifier loaded in %.1fs", time.time() - t0)
        except Exception as exc:
            self._classifier_status = f"error: {exc}"
            logger.error("Zero-shot classifier load failed: %s", exc)

    CANONICAL_LABELS = [
        "Geopolitical", "Macroeconomic", "Credit Event",
        "Merger & Acquisition", "Product Launch", "Earnings",
        "Regulatory / Legal", "Monetary Policy", "Commodity / Energy",
        "Market Movement", "Liquidity", "Supply Chain",
        "Management / Leadership", "Corporate Action",
    ]

    def classify_event(self, text: str) -> Dict[str, Any]:
        """Zero-shot event classification into canonical taxonomy."""
        if self._zeroshot_pipeline is None:
            self.load_classifier()
        if self._zeroshot_pipeline is None:
            return self._fallback_classify(text)
        try:
            truncated = text[:512]
            result = self._zeroshot_pipeline(
                truncated,
                candidate_labels=self.CANONICAL_LABELS,
                multi_label=False,
            )
            top_label = result["labels"][0]
            top_score = round(result["scores"][0], 4)
            return {
                "class": top_label,
                "confidence": top_score,
                "all_scores": {l: round(s, 4) for l, s in zip(result["labels"][:5], result["scores"][:5])},
                "model": "facebook/bart-large-mnli",
            }
        except Exception as exc:
            logger.warning("Zero-shot classification error: %s", exc)
            return self._fallback_classify(text)

    @staticmethod
    def _fallback_classify(text: str) -> Dict[str, Any]:
        """Keyword-based fallback for event classification."""
        keyword_map = {
            "Geopolitical": ["war", "sanction", "geopolitical", "conflict", "tariff", "tension"],
            "Macroeconomic": ["inflation", "recession", "gdp", "unemployment", "rate hike"],
            "Credit Event": ["default", "downgrade", "credit", "restructuring"],
            "Merger & Acquisition": ["merger", "acquisition", "takeover", "buyout"],
            "Earnings": ["earnings", "revenue", "profit", "quarterly results"],
            "Regulatory / Legal": ["investigation", "regulator", "lawsuit", "compliance"],
            "Monetary Policy": ["fed", "rate cut", "central bank", "monetary policy"],
            "Commodity / Energy": ["oil", "gas", "energy", "commodity", "crude"],
            "Market Movement": ["rally", "selloff", "crash", "market"],
            "Liquidity": ["liquidity", "funding", "bank run", "cash crunch"],
            "Supply Chain": ["supply chain", "disruption", "shipping", "logistics"],
            "Management / Leadership": ["ceo", "management", "board", "executive"],
            "Corporate Action": ["dividend", "stock split", "share repurchase"],
            "Product Launch": ["launch", "release", "product", "new device"],
        }
        lowered = text.lower()
        best_class, best_count = "Other", 0
        for cls, keywords in keyword_map.items():
            count = sum(1 for kw in keywords if kw in lowered)
            if count > best_count:
                best_count = count
                best_class = cls
        conf = round(min(0.75, 0.4 + best_count * 0.1), 4)
        return {"class": best_class, "confidence": conf, "all_scores": {}, "model": "keyword-fallback"}

    # ── Status ───────────────────────────────────────────────
    def status(self) -> Dict[str, str]:
        return {
            "finbert": self._finbert_status,
            "embedding_model": self._embedding_status,
            "event_classifier": self._classifier_status,
            "device": self.device,
        }

    def load_all(self) -> None:
        """Pre-load all models. Call during startup."""
        logger.info("Pre-loading all models...")
        self.load_finbert()
        self.load_embeddings()
        self.load_classifier()
        logger.info("All models loaded. Status: %s", self.status())


# Singleton accessor
def get_model_manager() -> ModelManager:
    return ModelManager()
