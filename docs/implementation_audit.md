# FinRisk Intelligence — Implementation Audit

**Date:** 2026-10-05
**Auditor:** Automated Deep Audit

---

## 1. Existing Functionality (What Partially Works)

- FastAPI app boots and serves routes
- Basic React frontend with react-router-dom, recharts, TanStack Query (imported but not used for data fetching)
- Docker Compose with postgres/redis/backend/frontend services
- Basic API structure: /health, /analyze, /ingest, /events, /entities, /portfolio, /stress-test, /metrics, /demo/run
- WebSocket endpoint exists at /ws/risk-events
- Config files exist for entities, taxonomy, stress scenarios

## 2. Broken Functionality

| Area | Issue |
|------|-------|
| WebSocket | `broadcast_event()` calls sync `send_json()` from async context — will silently fail |
| Stress Engine | Line 41: `impacted = value * (loss_percent if loss_percent < 0 else 0.0)` — **ignores all positive shocks** (commodity price increase, spread widening, default rates) |
| Alembic | No migration files exist (only README.md in migrations/). `alembic upgrade head || true` silently ignores failure |
| Database | Configured for PostgreSQL in docker-compose but defaults to SQLite in code. **No SQLAlchemy models exist** |
| Demo seed | Claims source "Reuters" and "Bloomberg" — never actually fetches from these sources |
| Health endpoint | Hardcodes `"redis": "ready"` without checking Redis, `"model_status": "risk-engine-active"` without checking models |

## 3. Mock/Stub Functionality

| Component | Issue |
|-----------|-------|
| `download_datasets.py` | Creates empty directories and fake manifests with `"rows": 0, "status": "stubbed-local"`. **No actual downloads** |
| `RSSNewsSource.fetch()` | Returns fabricated hardcoded strings, never calls any RSS feed |
| `DatasetSource.fetch()` | Returns 2 hardcoded strings, never loads any dataset |
| `sentiment_analysis()` | Pure keyword matching with NEGATIVE_WORDS/POSITIVE_WORDS lists. **No FinBERT** |
| `extract_entities()` | Dictionary lookup only (`if "apple" in text`). **No NER model** |
| `classify_event()` | Keyword matching against EVENT_KEYWORDS dict. **No ML classifier** |
| `evaluate_models.py` | Uses 3 hand-written examples, hardcodes `impact_mae: 1.6`, `impact_rmse: 1.9` |
| Corroboration | Text substring matching, not semantic similarity |
| Novelty | Word overlap ratio, not embedding similarity |
| Source credibility | Hardcoded values based on source name substrings |

## 4. Hard-coded Functionality

| Location | Hardcoded Value |
|----------|----------------|
| `App.tsx:82-88` | Risk timeline `[{time:'09:00', risk:4.1}, ...]` — never fetched from backend |
| `App.tsx:108` | Fallback `8.7 / 10` for overall risk |
| `App.tsx:109` | Fallback `'3'` for high-risk events |
| `App.tsx:110` | Fallback `'1'` for critical events |
| `App.tsx:111` | Fallback `-0.6` for sentiment |
| `App.tsx:112` | Fallback `14` for events processed |
| `App.tsx:131` | Hardcoded "ACCELERATING" badge |
| `App.tsx:156-159` | Hardcoded stress test: $100M → $89.1M → -$10.9M |
| `App.tsx:174` | Hardcoded fallback event with specific values |
| `App.tsx:184` | Hardcoded "Entity: Apple" |
| `App.tsx:223-226` | Hardcoded source credibility scores |
| `App.tsx:232-234` | Hardcoded model status "live", "active", "ready" |
| `risk_fusion.py:98` | `market_volatility: 0.72` |
| `metrics.py:21-22` | `portfolio_exposure: 0.7`, `market_risk: "ELEVATED"` |
| `impact_scorer.py:39` | Confidence hardcoded to 0.85, 0.9, 0.5 in entity extractor |

## 5. Missing Functionality

- **No SQLAlchemy ORM models** — no database schema
- **No Alembic migrations** — only an empty migrations directory
- **No FinBERT model** — transformers/torch listed in requirements but never imported
- **No sentence-transformers** — listed but never used
- **No event clustering / deduplication**
- **No proper entity extraction (NER)**
- **No Redis usage** — redis package installed but never imported
- **No real WebSocket broadcasting** (sync call in async context)
- **No event lifecycle (NEW/DEVELOPING/ESCALATING/STABLE/RESOLVED)**
- **No /events/:eventId detail page** in frontend
- **No /entities/:entityId detail page** in frontend
- **No /settings route** in frontend
- **No search functionality**
- **No filters**
- **No loading/error/empty states**
- **No Run Demo button functionality** (navigates to raw API URL)
- **No ingestion UI**
- **No stress test execution UI**
- **No COMMODITY_SHOCK scenario**
- **No automatic stress trigger persistence**
- **No analytics/overview endpoint**
- **No model manager / model health**
- **No impact score explainability (component breakdown)**
- **No responsive design / sidebar collapse**

## 6. Dataset Problems

- `download_datasets.py` creates stub manifests with `rows: 0`
- No actual Hugging Face datasets are downloaded
- No data files exist in `data/raw/`
- No `data/README.md` explaining datasets and licenses

## 7. NLP Problems

- Sentiment: keyword matching only, no FinBERT
- Entity extraction: dictionary lookup only, no NER
- Event classification: keyword matching only, no ML model
- No zero-shot classification
- No embeddings
- No semantic similarity
- Confidence values are fabricated formulas

## 8. Frontend Problems

- Entire app is in one `App.tsx` file (388 lines)
- No component architecture
- No API client layer (TanStack Query imported but not used)
- No event detail page
- No entity detail page
- No settings page
- Run Demo button: `window.location.assign('/api/v1/demo/run')` — navigates to raw JSON
- Dark-only theme, no light mode
- Hardcoded fallback data everywhere
- No loading states, error states, or empty states
- No search, no filters
- No responsive design
- No reusable components (KpiCard, EventTable, etc.)

## 9. Backend Problems

- All state stored in Python list (`self.history`)
- No PostgreSQL integration (despite docker-compose config)
- No Redis integration
- WebSocket broadcast is synchronous in async context
- No Pydantic response models
- No pagination, filtering, sorting
- No proper error handling
- Services instantiated per-request in routes
- No model loading/caching
- Portfolio service reads from JSON file only

## 10. Database Problems

- No SQLAlchemy models defined
- No Alembic migrations
- alembic.ini points to sqlite despite PostgreSQL in docker-compose
- `|| true` in Dockerfile hides migration failures
- No database initialization
- No wait-for-db logic

## 11. Docker Problems

- Backend Dockerfile: `alembic upgrade head || true` hides errors
- No model cache volume
- No HF_HOME volume
- Frontend: VITE_API_BASE_URL is set to localhost (won't work for Docker networking)
- No worker service for model inference
- No proper startup ordering beyond healthchecks

## 12. Testing Problems

- Single test file `test_core.py` with basic tests
- No integration tests
- No frontend tests
- No WebSocket tests
- No stress engine tests
- No API validation tests

---

## Priority Rebuild Order

1. Database schema + migrations + PostgreSQL integration
2. Real NLP services (FinBERT, embeddings, NER, classification)
3. Real data ingestion (RSS, dataset replay)
4. Risk fusion with database persistence
5. Stress engine fix + full scenarios
6. Redis pub/sub + WebSocket
7. Complete API with Pydantic models
8. Frontend complete rebuild with routing, components, design system
9. Dataset download script
10. Evaluation scripts
11. Docker + testing
12. Documentation
