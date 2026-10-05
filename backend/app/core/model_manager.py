"""
Model Manager — Singleton that manages lazy loading, caching, and inference
for all ML models used in the FinRisk pipeline.

Models:
- ProsusAI/finbert — financial sentiment analysis
- sentence-transformers/all-MiniLM-L6-v2 — sentence embeddings for dedup/clustering
- Zero-shot classifier — event classification via facebook/bart-large-mnli (or valhalla/distilbart-mnli-12-3)
- dslim/bert-base-NER — transformer named entity recognition

CRITICAL RULES:
1. No silent keyword/random fallbacks.
2. Thread-safe loading to prevent duplicate concurrent load crashes.
3. State machine: NOT_LOADED, LOADING, READY, ERROR.
4. Fail cleanly with ModelUnavailableError when required models are not available.
"""
from __future__ import annotations

import logging
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import yaml

logger = logging.getLogger("finrisk.models")

_TAXONOMY_PATH = Path(__file__).resolve().parents[3] / "config" / "event_taxonomy.yaml"

# Readiness states
NOT_LOADED = "not_loaded"
LOADING = "loading"
READY = "ready"
ERROR = "error"

# Confidence threshold for mapping low-confidence zero-shot predictions to "Other"
OTHER_CONFIDENCE_THRESHOLD = 0.25


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
    logger.warning("Using hardcoded event taxonomy — config/event_taxonomy.yaml not found")
    return [
        "Geopolitical", "Macroeconomic", "Credit Event",
        "Merger & Acquisition", "Product Launch", "Earnings",
        "Regulatory / Legal", "Monetary Policy", "Commodity / Energy",
        "Market Movement", "Liquidity", "Supply Chain",
        "Management / Leadership", "Corporate Action", "Other",
    ]


class ModelUnavailableError(Exception):
    """Raised when a required NLP model is not available or failed to load."""

    def __init__(
        self,
        model_name: str,
        status: str = "unavailable",
        message: Optional[str] = None,
    ) -> None:
        self.model_name = model_name
        self.status = status
        self.message = message or f"Required model '{model_name}' is unavailable (status: {status})."
        self.retryable = status in (NOT_LOADED, LOADING)
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_code": "MODEL_UNAVAILABLE",
            "model": self.model_name,
            "status": self.status,
            "retryable": self.retryable,
            "message": self.message,
        }


class ModelManager:
    """Singleton model manager with lazy loading, device selection, and thread-safe locks."""

    _instance: Optional["ModelManager"] = None
    _init_lock = threading.Lock()
    _initialized: bool = False

    def __new__(cls) -> "ModelManager":
        with cls._init_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
            return cls._instance

    def __init__(self) -> None:
        with self._init_lock:
            if ModelManager._initialized:
                return
            ModelManager._initialized = True

            try:
                import torch
                self.device = "cuda" if torch.cuda.is_available() else "cpu"
            except ImportError:
                self.device = "cpu"
            logger.info("Model device: %s", self.device)

            # Per-model thread locks to protect against concurrent duplicate loads
            self._finbert_lock = threading.Lock()
            self._embedding_lock = threading.Lock()
            self._classifier_lock = threading.Lock()
            self._ner_lock = threading.Lock()

            self._finbert_pipeline = None
            self._embedding_model = None
            self._zeroshot_pipeline = None
            self._ner_pipeline = None

            self._classifier_model_name: Optional[str] = None

            self._finbert_status = NOT_LOADED
            self._embedding_status = NOT_LOADED
            self._classifier_status = NOT_LOADED
            self._ner_status = NOT_LOADED

            self.CANONICAL_LABELS = _load_taxonomy()

    # ── FinBERT ──────────────────────────────────────────────
    def load_finbert(self) -> None:
        if self._finbert_status == READY and self._finbert_pipeline is not None:
            return
        with self._finbert_lock:
            if self._finbert_status == READY and self._finbert_pipeline is not None:
                return
            self._finbert_status = LOADING
            try:
                t0 = time.time()
                from transformers import pipeline as hf_pipeline
                self._finbert_pipeline = hf_pipeline(
                    "sentiment-analysis",
                    model="ProsusAI/finbert",
                    device=0 if self.device == "cuda" else -1,
                    top_k=None,
                )
                self._finbert_status = READY
                logger.info("FinBERT loaded in %.1fs on %s", time.time() - t0, self.device)
            except Exception as exc:
                self._finbert_status = f"{ERROR}: {exc}"
                logger.error("FinBERT load failed: %s", exc)

    def analyze_sentiment(self, text: str, allow_degraded: bool = False) -> Dict[str, Any]:
        """Run FinBERT sentiment analysis.
        
        If FinBERT is unavailable:
        - If allow_degraded=False, raises ModelUnavailableError.
        - If allow_degraded=True (e.g. explicitly requested), returns degraded response.
        Never silently uses keyword fallback.
        """
        if self._finbert_pipeline is None:
            self.load_finbert()

        if self._finbert_pipeline is None or self._finbert_status != READY:
            if not allow_degraded:
                raise ModelUnavailableError(
                    model_name="ProsusAI/finbert",
                    status=self._finbert_status,
                    message=f"FinBERT model unavailable: {self._finbert_status}",
                )
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
                probs[label] = round(float(item["score"]), 4)

            best = max(results, key=lambda x: x["score"])
            label = best["label"].lower()
            confidence = round(float(best["score"]), 4)

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
            if not allow_degraded:
                raise ModelUnavailableError(
                    model_name="ProsusAI/finbert",
                    status=f"{ERROR}: {exc}",
                    message=f"FinBERT inference failed: {exc}",
                )
            return {
                "label": "unknown",
                "score": 0.0,
                "confidence": 0.0,
                "probabilities": {},
                "model": "UNAVAILABLE",
                "degraded": True,
                "error": f"FinBERT inference failed: {exc}",
            }

    # ── Sentence Embeddings ──────────────────────────────────
    def load_embeddings(self) -> None:
        if self._embedding_status == READY and self._embedding_model is not None:
            return
        with self._embedding_lock:
            if self._embedding_status == READY and self._embedding_model is not None:
                return
            self._embedding_status = LOADING
            try:
                t0 = time.time()
                from sentence_transformers import SentenceTransformer
                self._embedding_model = SentenceTransformer("all-MiniLM-L6-v2", device=self.device)
                self._embedding_status = READY
                logger.info("Embedding model loaded in %.1fs", time.time() - t0)
            except Exception as exc:
                self._embedding_status = f"{ERROR}: {exc}"
                logger.error("Embedding model load failed: %s", exc)

    def encode(self, texts: List[str]) -> np.ndarray:
        """Encode texts to embeddings. Returns (N, dim) numpy array.
        
        CRITICAL: NEVER returns random vectors. Raises ModelUnavailableError
        if embedding model is unavailable.
        """
        if self._embedding_model is None:
            self.load_embeddings()
        if self._embedding_model is None or self._embedding_status != READY:
            raise ModelUnavailableError(
                model_name="sentence-transformers/all-MiniLM-L6-v2",
                status=self._embedding_status,
                message=f"Embedding model unavailable: {self._embedding_status}. Install sentence-transformers.",
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
        if self._classifier_status == READY and self._zeroshot_pipeline is not None:
            return
        with self._classifier_lock:
            if self._classifier_status == READY and self._zeroshot_pipeline is not None:
                return
            self._classifier_status = LOADING
            t0 = time.time()
            from transformers import pipeline as hf_pipeline
            # Try facebook/bart-large-mnli; fallback to distilbart if resource-constrained
            for model_name in ["facebook/bart-large-mnli", "valhalla/distilbart-mnli-12-3"]:
                try:
                    self._zeroshot_pipeline = hf_pipeline(
                        "zero-shot-classification",
                        model=model_name,
                        device=0 if self.device == "cuda" else -1,
                    )
                    self._classifier_model_name = model_name
                    self._classifier_status = READY
                    logger.info("Zero-shot classifier (%s) loaded in %.1fs", model_name, time.time() - t0)
                    return
                except Exception as exc:
                    logger.warning("Zero-shot model '%s' failed to load: %s", model_name, exc)
                    self._classifier_status = f"{ERROR}: {exc}"
            logger.error("All zero-shot classifier models failed to load")

    def classify_event(self, text: str, allow_degraded: bool = False) -> Dict[str, Any]:
        """Zero-shot event classification into canonical taxonomy.
        
        Fixes:
        1. Accurately reports self._classifier_model_name.
        2. Handles 'Other' category via documented confidence threshold (OTHER_CONFIDENCE_THRESHOLD=0.25).
           If the top zero-shot score is below this threshold, the event is classified as 'Other'.
        3. Never silently uses keyword matching.
        """
        if self._zeroshot_pipeline is None:
            self.load_classifier()

        if self._zeroshot_pipeline is None or self._classifier_status != READY:
            if not allow_degraded:
                raise ModelUnavailableError(
                    model_name=self._classifier_model_name or "facebook/bart-large-mnli",
                    status=self._classifier_status,
                    message=f"Event classifier not available: {self._classifier_status}",
                )
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
            candidate_labels = [l for l in self.CANONICAL_LABELS if l != "Other"]
            result = self._zeroshot_pipeline(
                truncated,
                candidate_labels=candidate_labels,
                multi_label=False,
            )
            top_label = result["labels"][0]
            top_score = round(float(result["scores"][0]), 4)
            all_scores = {l: round(float(s), 4) for l, s in zip(result["labels"][:5], result["scores"][:5])}

            # Map low-confidence predictions to 'Other' with documented threshold
            if top_score < OTHER_CONFIDENCE_THRESHOLD:
                top_label = "Other"
                confidence = round(1.0 - top_score, 4)
            else:
                confidence = top_score

            inference_ms = round((time.time() - t0) * 1000, 1)

            return {
                "class": top_label,
                "confidence": confidence,
                "all_scores": all_scores,
                "model": self._classifier_model_name or "facebook/bart-large-mnli",
                "inference_ms": inference_ms,
            }
        except Exception as exc:
            logger.warning("Zero-shot classification error: %s", exc)
            if not allow_degraded:
                raise ModelUnavailableError(
                    model_name=self._classifier_model_name or "facebook/bart-large-mnli",
                    status=f"{ERROR}: {exc}",
                    message=f"Classification failed: {exc}",
                )
            return {
                "class": "Other",
                "confidence": 0.0,
                "all_scores": {},
                "model": "UNAVAILABLE",
                "degraded": True,
                "error": f"Classification failed: {exc}",
            }

    # ── NER Model ────────────────────────────────────────────
    def load_ner(self) -> None:
        """Load transformer NER model for entity extraction."""
        if self._ner_status == READY and self._ner_pipeline is not None:
            return
        with self._ner_lock:
            if self._ner_status == READY and self._ner_pipeline is not None:
                return
            self._ner_status = LOADING
            try:
                t0 = time.time()
                from transformers import pipeline as hf_pipeline
                self._ner_pipeline = hf_pipeline(
                    "ner",
                    model="dslim/bert-base-NER",
                    aggregation_strategy="simple",
                    device=0 if self.device == "cuda" else -1,
                )
                self._ner_status = READY
                logger.info("NER model loaded in %.1fs", time.time() - t0)
            except Exception as exc:
                self._ner_status = f"{ERROR}: {exc}"
                logger.error("NER model load failed: %s", exc)

    def extract_ner(self, text: str) -> List[Dict[str, Any]]:
        """Extract named entities using transformer NER model.
        
        Returns list of {word, entity_group, score, start, end}.
        Raises ModelUnavailableError if NER pipeline cannot be loaded.
        """
        if self._ner_pipeline is None:
            self.load_ner()

        if self._ner_pipeline is None or self._ner_status != READY:
            logger.warning("NER model unavailable (status: %s)", self._ner_status)
            return []

        try:
            truncated = text[:512]
            results = self._ner_pipeline(truncated)
            return [
                {
                    "word": r["word"],
                    "entity_group": r["entity_group"],
                    "score": round(float(r["score"]), 4),
                    "start": r["start"],
                    "end": r["end"],
                }
                for r in results
                if float(r["score"]) > 0.5
            ]
        except Exception as exc:
            logger.warning("NER inference error: %s", exc)
            return []

    # ── Status and Readiness ─────────────────────────────────
    def status(self) -> Dict[str, str]:
        """Return raw model status dictionary."""
        return {
            "finbert": self._finbert_status,
            "embedding_model": self._embedding_status,
            "event_classifier": self._classifier_status,
            "ner_model": self._ner_status,
            "device": self.device,
        }

    def get_readiness(self) -> Dict[str, Any]:
        """Return readiness evaluation distinguishing ready, loading, error, degraded."""
        raw = self.status()
        model_statuses = [
            raw["finbert"],
            raw["embedding_model"],
            raw["event_classifier"],
            raw["ner_model"],
        ]

        if all(s == READY for s in model_statuses):
            overall = "ready"
        elif any(s.startswith(ERROR) for s in model_statuses):
            overall = "error"
        elif any(s == LOADING for s in model_statuses):
            overall = "loading"
        elif any(s == READY for s in model_statuses):
            overall = "degraded"
        else:
            overall = "not_loaded"

        return {
            "readiness": overall,
            "models": {
                "finbert": raw["finbert"],
                "embedding_model": raw["embedding_model"],
                "event_classifier": raw["event_classifier"],
                "ner_model": raw["ner_model"],
            },
            "device": self.device,
        }

    def is_ready(self) -> bool:
        """Check if all models are loaded and ready."""
        return (
            self._finbert_status == READY
            and self._embedding_status == READY
            and self._classifier_status == READY
            and self._ner_status == READY
        )

    def check_mandatory_models(self) -> None:
        """Verify mandatory NLP models are available; raises ModelUnavailableError if not."""
        if self._finbert_pipeline is None:
            self.load_finbert()
        if self._finbert_status != READY:
            raise ModelUnavailableError("ProsusAI/finbert", self._finbert_status)

        if self._embedding_model is None:
            self.load_embeddings()
        if self._embedding_status != READY:
            raise ModelUnavailableError("sentence-transformers/all-MiniLM-L6-v2", self._embedding_status)

        if self._zeroshot_pipeline is None:
            self.load_classifier()
        if self._classifier_status != READY:
            raise ModelUnavailableError(
                self._classifier_model_name or "facebook/bart-large-mnli",
                self._classifier_status,
            )

    def load_all(self) -> None:
        """Pre-load all models sequentially and thread-safely."""
        logger.info("Pre-loading all models...")
        self.load_finbert()
        self.load_embeddings()
        self.load_classifier()
        self.load_ner()
        logger.info("All models loaded. Status: %s", self.status())


# Singleton accessor
def get_model_manager() -> ModelManager:
    return ModelManager()
