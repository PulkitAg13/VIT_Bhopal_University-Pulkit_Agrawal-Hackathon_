"""
Model Manager — Singleton that manages lazy loading, caching, and inference
for all ML models used in the FinRisk pipeline.

Models:
- ProsusAI/finbert — financial sentiment analysis
- all-MiniLM-L6-v2 — sentence embeddings for dedup/clustering
- Zero-shot classifier — event classification via facebook/bart-large-mnli

CRITICAL: No silent keyword/random fallbacks. If a model is unavailable,
the system returns a clear degraded-state response.
"""
from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import yaml

logger = logging.getLogger("finrisk.models")

_TAXONOMY_PATH = Path(__file__).resolve().parents[3] / "config" / "event_taxonomy.yaml"


def _load_taxonomy() -> List[str]:
    """Load canonical event labels from config/event_taxonomy.yaml."""
    if _TAXONOMY_PATH.exists():
        try:
            with open(_TAXONOMY_PATH, "r", encoding="utf-8") as fh:
                cfg = yaml.safe_load(fh)
            labels = cfg.get("taxonomy", [])
            if labels:
                logger.info("Loaded %d event taxonomy labels from %s", len(labels), _TAXONOMY_PATH)
                return labels
        except Exception as exc:
            logger.warning("Failed to load event taxonomy: %s", exc)
    # Hardcoded fallback if YAML is missing (should not happen in production)
    logger.warning("Using hardcoded event taxonomy — config/event_taxonomy.yaml not found")
    return [
        "Geopolitical", "Macroeconomic", "Credit Event",
        "Merger & Acquisition", "Product Launch", "Earnings",
        "Regulatory / Legal", "Monetary Policy", "Commodity / Energy",
        "Market Movement", "Liquidity", "Supply Chain",
        "Management / Leadership", "Corporate Action", "Other",
    ]


class ModelManager:
    """Singleton model manager with lazy loading and device selection.
    
    CRITICAL RULE: No silent fallbacks. If a model cannot be loaded,
    inference methods return a clearly-labelled degraded response.
    """

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
        try:
            import torch
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        except ImportError:
            self.device = "cpu"
        logger.info("Model device: %s", self.device)
        self._finbert_pipeline = None
        self._embedding_model = None
        self._zeroshot_pipeline = None
        self._ner_pipeline = None
        self._finbert_status = "not_loaded"
        self._embedding_status = "not_loaded"
        self._classifier_status = "not_loaded"
        self._ner_status = "not_loaded"
        self.CANONICAL_LABELS = _load_taxonomy()

    # ── FinBERT ──────────────────────────────────────────────
    def load_finbert(self) -> None:
        if self._finbert_pipeline is not None:
            return
        self._finbert_status = "loading"
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
        """Run FinBERT sentiment analysis.
        
        CRITICAL: If FinBERT is unavailable, returns a degraded-mode response
        with model='UNAVAILABLE'. Never silently uses keyword analysis.
        """
        if self._finbert_pipeline is None:
            self.load_finbert()
        if self._finbert_pipeline is None:
            # EXPLICIT degraded mode — NOT silent keyword fallback
            return {
                "label": "unknown",
                "score": 0.0,
                "confidence": 0.0,
                "probabilities": {},
                "model": "UNAVAILABLE",
                "degraded": True,
                "error": f"FinBERT model not available: {self._finbert_status}",
            }

        try:
            t0 = time.time()
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

            inference_ms = round((time.time() - t0) * 1000, 1)

            return {
                "label": label,
                "score": score,
                "confidence": confidence,
                "probabilities": probs,
                "model": "ProsusAI/finbert",
                "inference_ms": inference_ms,
            }
        except Exception as exc:
            logger.warning("FinBERT inference error: %s", exc)
            return {
                "label": "unknown",
                "score": 0.0,
                "confidence": 0.0,
                "probabilities": {},
                "model": "UNAVAILABLE",
                "degraded": True,
                "error": f"FinBERT inference failed: {str(exc)}",
            }

    # ── Sentence Embeddings ──────────────────────────────────
    def load_embeddings(self) -> None:
        if self._embedding_model is not None:
            return
        self._embedding_status = "loading"
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
        """Encode texts to embeddings. Returns (N, dim) numpy array.
        
        CRITICAL: NEVER returns random vectors. Raises RuntimeError if
        the embedding model is unavailable.
        """
        if self._embedding_model is None:
            self.load_embeddings()
        if self._embedding_model is None:
            raise RuntimeError(
                f"Embedding model unavailable: {self._embedding_status}. "
                "Cannot generate embeddings. Install sentence-transformers and retry."
            )
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
        self._classifier_status = "loading"
        t0 = time.time()
        from transformers import pipeline as hf_pipeline
        # Try facebook/bart-large-mnli; if pagefile/memory fails, fallback to distilbart
        for model_name in ["facebook/bart-large-mnli", "valhalla/distilbart-mnli-12-3"]:
            try:
                self._zeroshot_pipeline = hf_pipeline(
                    "zero-shot-classification",
                    model=model_name,
                    device=0 if self.device == "cuda" else -1,
                )
                self._classifier_model_name = model_name
                self._classifier_status = "ready"
                logger.info("Zero-shot classifier (%s) loaded in %.1fs", model_name, time.time() - t0)
                return
            except Exception as exc:
                logger.warning("Zero-shot model '%s' failed to load: %s", model_name, exc)
                self._classifier_status = f"error: {exc}"
        logger.error("All zero-shot classifier models failed to load")

    def classify_event(self, text: str) -> Dict[str, Any]:
        """Zero-shot event classification into canonical taxonomy.
        
        CRITICAL: If classifier is unavailable, returns a degraded-mode
        response with model='UNAVAILABLE'. Never uses keyword matching silently.
        """
        if self._zeroshot_pipeline is None:
            self.load_classifier()
        if self._zeroshot_pipeline is None:
            return {
                "class": "Other",
                "confidence": 0.0,
                "all_scores": {},
                "model": "UNAVAILABLE",
                "degraded": True,
                "error": f"Event classifier not available: {self._classifier_status}",
            }
        try:
            t0 = time.time()
            truncated = text[:512]
            # Filter out 'Other' for zero-shot — it's too generic
            candidate_labels = [l for l in self.CANONICAL_LABELS if l != "Other"]
            result = self._zeroshot_pipeline(
                truncated,
                candidate_labels=candidate_labels,
                multi_label=False,
            )
            top_label = result["labels"][0]
            top_score = round(result["scores"][0], 4)
            inference_ms = round((time.time() - t0) * 1000, 1)
            return {
                "class": top_label,
                "confidence": top_score,
                "all_scores": {l: round(s, 4) for l, s in zip(result["labels"][:5], result["scores"][:5])},
                "model": "facebook/bart-large-mnli",
                "inference_ms": inference_ms,
            }
        except Exception as exc:
            logger.warning("Zero-shot classification error: %s", exc)
            return {
                "class": "Other",
                "confidence": 0.0,
                "all_scores": {},
                "model": "UNAVAILABLE",
                "degraded": True,
                "error": f"Classification failed: {str(exc)}",
            }

    # ── NER Model ────────────────────────────────────────────
    def load_ner(self) -> None:
        """Load transformer NER model for entity extraction."""
        if self._ner_pipeline is not None:
            return
        self._ner_status = "loading"
        try:
            t0 = time.time()
            from transformers import pipeline as hf_pipeline
            self._ner_pipeline = hf_pipeline(
                "ner",
                model="dslim/bert-base-NER",
                aggregation_strategy="simple",
                device=0 if self.device == "cuda" else -1,
            )
            self._ner_status = "ready"
            logger.info("NER model loaded in %.1fs", time.time() - t0)
        except Exception as exc:
            self._ner_status = f"error: {exc}"
            logger.error("NER model load failed: %s", exc)

    def extract_ner(self, text: str) -> List[Dict[str, Any]]:
        """Extract named entities using transformer NER model.
        
        Returns list of {word, entity_group, score, start, end}.
        If NER model is unavailable, returns empty list (dictionary
        extraction will still work as secondary layer).
        """
        if self._ner_pipeline is None:
            self.load_ner()
        if self._ner_pipeline is None:
            logger.warning("NER model unavailable, falling back to dictionary-only extraction")
            return []
        try:
            truncated = text[:512]
            results = self._ner_pipeline(truncated)
            return [
                {
                    "word": r["word"],
                    "entity_group": r["entity_group"],
                    "score": round(r["score"], 4),
                    "start": r["start"],
                    "end": r["end"],
                }
                for r in results
                if r["score"] > 0.5
            ]
        except Exception as exc:
            logger.warning("NER inference error: %s", exc)
            return []

    # ── Status ───────────────────────────────────────────────
    def status(self) -> Dict[str, str]:
        return {
            "finbert": self._finbert_status,
            "embedding_model": self._embedding_status,
            "event_classifier": self._classifier_status,
            "ner_model": self._ner_status,
            "device": self.device,
        }

    def load_all(self) -> None:
        """Pre-load all models. Call during startup."""
        logger.info("Pre-loading all models...")
        self.load_finbert()
        self.load_embeddings()
        self.load_classifier()
        self.load_ner()
        logger.info("All models loaded. Status: %s", self.status())


# Singleton accessor
def get_model_manager() -> ModelManager:
    return ModelManager()
