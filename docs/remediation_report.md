# FinRisk Intelligence — Engineering Remediation & Verification Report

**Status:** VERIFIED
**Date:** 2026-10-08
**Scope:** Remediation of NLP pipelines, model evaluation, health safety, frontend error resilience, and automated verification.

---

## 1. Remediation Summary & Current Architecture

### Real Model Integration (Zero Fallback)
1. **ProsusAI/finbert Sentiment:**
   - Mandatory model for sentiment analysis.
   - Raises controlled `ModelUnavailableError` (HTTP 503) if unavailable or failed. No keyword fallback.
2. **all-MiniLM-L6-v2 Embeddings:**
   - Mandatory for text embedding, clustering, and novelty calculation.
   - Raises controlled `ModelUnavailableError` (HTTP 503) if unavailable. No random vectors.
3. **facebook/bart-large-mnli Zero-Shot Event Classifier:**
   - Mandatory for canonical event taxonomy classification.
   - Low confidence mapped to "Other" with documented threshold (`OTHER_CONFIDENCE_THRESHOLD = 0.25`).
   - Raises controlled `ModelUnavailableError` (HTTP 503) if unavailable. No keyword fallback.
4. **dslim/bert-base-NER Transformer Entity Recognition:**
   - Mandatory model checked in `ModelManager.check_mandatory_models()`.
   - Normal `/analyze` and `/ingest` pipelines return controlled `ModelUnavailableError` (HTTP 503) if NER is unavailable.
   - Secondary dictionary, alias, and pattern layers act strictly as enrichment after successful transformer NER.

### Real Recency Calculation
- Timezone-aware delta computed from `published_at`, document/source retrieval timestamp (`retrieved_at`), or creation timestamp (`created_at`).
- If no usable timestamp is provided, recency is explicitly marked as unavailable (`recency_available=False`, scored at 0.0 with explanation note), rather than fabricating freshness as 0.0 hours old.

### Safe Health Probes
- Database exceptions and internal errors are logged server-side with stack traces (`logger.error`).
- `/api/v1/health` and `/api/v1/readiness` return safe enum statuses (`connected`, `error`, `unavailable`, `ready`, `degraded`) without leaking raw exception strings or database internals.

### Frontend Resilience & Filtering
- All swallowed `.catch(() => {})` and `.catch(() => null)` blocks removed from `Dashboard`, `Portfolio`, `SettingsPage`, `Analytics`, `LiveFeed`, and `StressTesting`.
- Every page provides an explicit error state with an interactive `Retry` button.
- `Events.tsx` includes `sentiment` and `source` filters alongside `event_class`, `risk_level`, `search`, and pagination.

---

## 2. Model Evaluation (Deterministic Stratified Sampling)

Evaluated via `scripts/evaluate_models.py` with deterministic stratified sampling across real HuggingFace test/validation datasets:
- **Twitter Financial News Sentiment** (`zeroshot/twitter-financial-news-sentiment`): Evaluated with balanced support (10 Negative, 10 Neutral, 10 Positive). Macro F1: 0.6019.
- **Financial PhraseBank** (`takala/financial_phrasebank`): Evaluated with balanced support (10 Negative, 10 Neutral, 10 Positive). Accuracy: 93.33%, Macro F1: 0.9327.
- **Twitter Financial News Topic** (`zeroshot/twitter-financial-news-topic`): Evaluated with deterministic representation across all 13 canonical taxonomy categories with meaningful support (support=2 per class). Accuracy: 46.15%, Macro F1: 0.3755.
- Results and full confusion matrices documented in `docs/model_evaluation.md`.

---

## 3. Targeted Test Suite & Verification Results

The test suite covers:
1. `test_ner_unavailable_raises_model_unavailable`: Controlled HTTP 503 returned when NER model is unavailable.
2. `test_duplicate_ingestion_returns_already_processed`: Deterministic duplicate protection flags `already_processed: True`.
3. `test_non_eligible_high_impact_event_does_not_trigger_stress`: High impact non-eligible categories (e.g. Product Launch) do not trigger stress simulations.
4. `test_eligible_high_impact_event_persists_automatic_stress_simulation`: High impact eligible categories (e.g. Geopolitical) automatically execute and persist `StressSimulation` linked to `RiskSignal`.
5. `test_events_sentiment_filter`: Event listing query filtered by `sentiment`.
6. `test_events_source_filter`: Event listing query filtered by `source`.
