# FinRisk Intelligence

AI-powered financial risk intelligence platform for wholesale banking, featuring real-time NLP event processing, stress testing, and explainable risk scoring.

## Architecture

```
┌─────────────────────────────────────────────────┐
│                    Frontend                     │
│  React + TypeScript + Vite + Recharts           │
│  Sidebar nav · Dashboard · Events · Entities    │
│  Portfolio · Stress Testing · Analytics         │
└──────────────────────┬──────────────────────────┘
                       │ HTTP / WebSocket
┌──────────────────────┴──────────────────────────┐
│                  Backend (FastAPI)               │
│  /analyze · /ingest · /events · /entities       │
│  /portfolio · /stress-test · /metrics · /demo   │
├─────────────────────────────────────────────────┤
│              NLP Pipeline                       │
│  FinBERT sentiment · Zero-shot classification   │
│  Entity extraction · Sentence embeddings        │
│  Novelty · Corroboration · Impact scoring       │
├─────────────────────────────────────────────────┤
│              Infrastructure                     │
│  PostgreSQL · Redis pub/sub · WebSocket         │
└─────────────────────────────────────────────────┘
```

## Features

### Implemented End-to-End

- **FinBERT Sentiment Analysis** — ProsusAI/finbert for financial-domain sentiment
- **Zero-Shot Event Classification** — facebook/bart-large-mnli classifying into 15 event categories
- **Sentence Embeddings** — all-MiniLM-L6-v2 for deduplication, novelty, corroboration
- **Entity Extraction** — Config-driven dictionary + regex with entity resolution
- **Explainable Impact Scoring** — 9-component weighted formula with "Why this score?" breakdown
- **Event Clustering** — Cosine-similarity-based deduplication with lifecycle (NEW → DEVELOPING → ESCALATING)
- **Stress Testing Engine** — 5 scenarios with asset-level impact across 6 asset classes
- **Real-Time Pipeline** — Redis pub/sub → WebSocket broadcasting
- **Database Persistence** — PostgreSQL with full ORM (sources, documents, entities, signals, clusters, portfolio, simulations)
- **Yahoo Finance RSS** — Live financial news ingestion via feedparser
- **Dataset Replay** — Replay HuggingFace datasets through the pipeline
- **Portfolio Service** — 18-position synthetic wholesale banking portfolio ($100M)

### Data Sources

| Source | Type | Implementation |
|--------|------|----------------|
| Yahoo Finance RSS | Live | feedparser → RSS XML parsing |
| Twitter Financial News Topic | Dataset | HuggingFace datasets library |
| Twitter Financial News Sentiment | Dataset | HuggingFace datasets library |
| Financial PhraseBank | Dataset | HuggingFace datasets library |

### Models

| Model | Purpose | Source |
|-------|---------|--------|
| ProsusAI/finbert | Financial sentiment | HuggingFace |
| all-MiniLM-L6-v2 | Sentence embeddings | sentence-transformers |
| facebook/bart-large-mnli | Event classification | HuggingFace |

## Quick Start

### Docker Compose (Recommended)

```bash
# Clone and start
git clone <repo>
cd VIT_Bhopal_University-Pulkit_Agrawal-Hackathon_

# Start all services
docker compose up --build

# Access:
# Frontend: http://localhost:3000
# Backend:  http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Local Development

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

### Download Datasets

```bash
pip install datasets
python scripts/download_datasets.py
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/health` | System health (DB, Redis, models) |
| POST | `/api/v1/analyze` | Run full NLP + risk pipeline on text |
| POST | `/api/v1/ingest` | Fetch from sources and analyze |
| GET | `/api/v1/events` | List events (with filters, pagination) |
| GET | `/api/v1/events/:id` | Event detail with explainability |
| GET | `/api/v1/entities` | List detected entities |
| GET | `/api/v1/entities/:id` | Entity detail with timelines |
| GET | `/api/v1/portfolio` | Portfolio positions |
| GET | `/api/v1/portfolio/exposure` | Portfolio exposure breakdown |
| GET | `/api/v1/stress-test/scenarios` | Available stress scenarios |
| POST | `/api/v1/stress-test` | Run stress test on portfolio |
| GET | `/api/v1/stress-test/results` | Stress test history |
| GET | `/api/v1/metrics` | Aggregated risk metrics |
| GET | `/api/v1/analytics/overview` | Full analytics with distributions |
| GET | `/api/v1/risk/timeline` | Risk trajectory data |
| POST | `/api/v1/demo/run` | Run full pipeline demo |
| WS | `/ws/risk-events` | Real-time event stream |

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI app with lifespan
│   │   ├── models.py                  # SQLAlchemy ORM models
│   │   ├── schemas.py                 # Pydantic request/response schemas
│   │   ├── api/
│   │   │   ├── dependencies.py        # Service singletons
│   │   │   └── routes/                # All API route handlers
│   │   ├── core/
│   │   │   ├── config.py              # Settings (env-driven)
│   │   │   ├── database.py            # PostgreSQL engine/session
│   │   │   ├── model_manager.py       # ML model singleton manager
│   │   │   ├── redis_client.py        # Redis pub/sub client
│   │   │   └── logging.py             # Structured logging
│   │   └── services/
│   │       ├── nlp/
│   │       │   ├── sentiment.py       # FinBERT sentiment
│   │       │   ├── event_classifier.py # Zero-shot classification
│   │       │   └── entity_extractor.py # Entity extraction + resolution
│   │       ├── risk/
│   │       │   ├── risk_fusion.py      # Full risk pipeline
│   │       │   └── impact_scorer.py    # Explainable impact scoring
│   │       ├── stress/
│   │       │   └── stress_engine.py    # Portfolio stress testing
│   │       ├── portfolio/
│   │       │   └── portfolio_service.py # Portfolio management
│   │       └── ingestion/
│   │           └── sources.py          # RSS + dataset + demo sources
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.tsx                    # Shell with sidebar routing
│   │   ├── api/client.ts             # Typed API client
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx          # Risk command center
│   │   │   ├── LiveFeed.tsx           # Real-time event feed
│   │   │   ├── Events.tsx             # Event list with filters
│   │   │   ├── EventDetail.tsx        # Event detail + explainability
│   │   │   ├── Entities.tsx           # Entity risk monitor
│   │   │   ├── EntityDetail.tsx       # Entity timelines
│   │   │   ├── Portfolio.tsx          # Portfolio positions + charts
│   │   │   ├── StressTesting.tsx      # Stress test runner
│   │   │   ├── Analytics.tsx          # Distributions + charts
│   │   │   └── SettingsPage.tsx       # Manual analysis + status
│   │   └── index.css                  # Professional design system
│   ├── Dockerfile
│   └── nginx.conf
├── config/
│   ├── entities.yaml                  # Entity resolution table
│   ├── event_taxonomy.yaml            # 15-category event taxonomy
│   └── stress_scenarios.yaml          # 5 stress scenarios with assumptions
├── scripts/
│   └── download_datasets.py           # Real HuggingFace dataset downloader
├── data/
│   └── README.md                      # Dataset documentation
├── docs/
│   └── implementation_audit.md        # Technical audit report
└── docker-compose.yml                 # Full stack orchestration
```

## Hardware Requirements

- **CPU:** The system runs on CPU. Models are automatically loaded on CPU when no GPU is available.
- **GPU:** If CUDA is available, models will automatically use GPU for faster inference.
- **RAM:** ~4GB recommended for model loading (FinBERT + embeddings + classifier).
- **Disk:** ~3GB for model downloads on first run.

## License

MIT
