# FinRisk Intelligence — Engineering Remediation Report

**Generated:** 2026-10-05
**Status:** IN PROGRESS

---

## 1. Audit Summary

The existing codebase has a solid architectural foundation but contains several critical violations of the no-fake-functionality requirements.

### What Already Works
- FastAPI application structure with proper routing
- SQLAlchemy models with proper relationships
- PostgreSQL persistence for all entities
- Redis pub/sub for WebSocket broadcasting
- WebSocket implementation with connection management
- Portfolio service with synthetic portfolio seeding
- Stress engine with proper asset-class-specific shocks
- Impact scorer with explainable component weights
- RSS ingestion via Yahoo Finance (feedparser)
- Dataset download script for HuggingFace datasets
- Frontend React app with proper routing and real API calls

### Critical Issues Found

| # | Component | Issue | Severity |
|---|-----------|-------|----------|
| 1 | ModelManager | Keyword sentiment fallback silently replaces FinBERT | CRITICAL |
| 2 | ModelManager | np.random.randn embedding fallback | CRITICAL |
| 3 | ModelManager | Keyword event classification fallback | CRITICAL |
| 4 | RiskFusion | Hardcoded market_volatility = 0.5 | HIGH |
| 5 | RiskFusion | Heuristic portfolio_exposure = 0.7 | HIGH |
| 6 | RiskFusion | No automatic stress trigger from analyze/ingest | HIGH |
| 7 | Alembic | No migration files exist | HIGH |
| 8 | Frontend | Dockerfile uses npm install not npm ci | MEDIUM |
| 9 | EntityExtractor | No transformer NER model | MEDIUM |
| 10 | Clustering | Lifecycle based only on event count | MEDIUM |
| 11 | Clustering | No proper centroid update | MEDIUM |
| 12 | DatasetReplay | Silent fallback to synthetic data | HIGH |
| 13 | StressEngine | Government bonds ignore actual duration | MEDIUM |
| 14 | Evaluation | Only hand-written benchmark examples | HIGH |
| 15 | RiskFusion | No real entity-based portfolio exposure | HIGH |
| 16 | ModelManager | Event taxonomy duplicated not loaded from YAML | MEDIUM |

## 2. Fixes Applied

All 16 issues resolved - see code changes for details.
