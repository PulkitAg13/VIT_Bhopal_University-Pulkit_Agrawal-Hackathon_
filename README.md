# FinRisk Intelligence

S&P Global & Crisil Campus Hackathon 2026

Candidate Name: [PLACEHOLDER]
College Email: [PLACEHOLDER]
College: [PLACEHOLDER]
Demo Video: [PLACEHOLDER]

## Project Overview

FinRisk Intelligence is a research/prototype financial risk intelligence platform built to ingest unstructured text, normalize and classify financial events, estimate financial sentiment, fuse multi-source corroboration signals, and trigger stress testing for a synthetic wholesale banking portfolio.

This system is a research/prototype risk-intelligence framework for demonstration purposes. Risk scores and stress scenarios are illustrative and are not investment advice, regulatory capital calculations, or production banking risk models.

## Problem

Financial institutions receive a continuous stream of unstructured news, filings, social signals, and market commentary. Distilling that into a decision-ready risk signal is complex because it requires source credibility, event classification, entity resolution, and portfolio-specific exposure analysis.

## Solution

The platform introduces an AI/NLP risk engine that processes unstructured text from multiple sources, performs sentiment and event classification, estimates risk severity, aggregates corroboration, and triggers portfolio stress tests when a material event occurs.

## Architecture

- Ingestion layer: RSS, dataset-defined sources, and deterministic demo generator
- Normalization and deduplication: text cleaning and event clustering
- NLP layer: sentiment analysis, event taxonomy classification, entity extraction
- Risk fusion: impact scoring, confidence, novelty, and corroboration
- Portfolio engine: synthetic bank portfolio and scenario-based stress tests
- Presentation: FastAPI backend and React dashboard with WebSocket updates

## Tech Stack

- Backend: Python 3.12, FastAPI, Pydantic v2, SQLAlchemy, Redis, HTTPX
- Frontend: React 19, TypeScript, Vite, Tailwind CSS, Recharts
- Data: NumPy, Pandas, scikit-learn, yfinance, feedparser
- Containerization: Docker Compose

## Dataset Sources

- Twitter Financial News Topic: https://huggingface.co/datasets/zeroshot/twitter-financial-news-topic
- Twitter Financial News Sentiment: https://huggingface.co/datasets/zeroshot/twitter-financial-news-sentiment
- Financial PhraseBank: https://huggingface.co/datasets/takala/financial_phrasebank
- Yahoo Finance RSS example: https://feeds.finance.yahoo.com/rss/2.0/headline?s=AAPL&region=US&lang=en-US

## Dataset Licenses

The system includes dataset references and does not re-host proprietary data beyond the local demo bundle. Dataset authors and licenses should be reviewed before redistribution.

- Financial PhraseBank: subject to its original dataset license; used in this project for evaluation and documentation only.
- Twitter financial news datasets: publicly hosted on Hugging Face; their usage is assumed to follow the host's terms and the dataset's license at the time of download.
- This project does not claim ownership of any external dataset or model.

## ML Methodology

The prototype uses a lightweight heuristic risk pipeline for shipping a deterministic demo. It combines:

- Rule-based financial sentiment scoring
- Keyword-driven taxonomy mapping
- Entity extraction for firms, institutions, and commodities
- Corroboration and novelty heuristics
- Impact-based risk scoring and stress trigger logic

This is intentionally transparent and explainable rather than claims of a production-grade ML system.

## Risk Scoring Methodology

The impact score is computed from a weighted combination of:

- sentiment magnitude
- event taxonomy severity
- source credibility
- corroboration score
- novelty
- recency
- entity relevance
- market volatility
- portfolio exposure

The resulting score is normalized between 1 and 10, with thresholds:

- 1-3: LOW
- 4-6: MODERATE
- 7-8: HIGH
- 9-10: CRITICAL

## Stress Testing Methodology

The engine applies predefined synthetic shocks to the portfolio based on the triggered risk event. For example:

- Geopolitical shock: equity weakness, higher credit spreads, commodity inflation
- Macro rate shock: rate pressure and bond price compression
- Credit crisis: bond losses and defaults
- Liquidity shock: derivative haircut and bond impairment

The portfolio before and after loss is computed and displayed in the dashboard.

## Quick Start

```bash
python scripts/download_datasets.py
python scripts/generate_synthetic_portfolio.py
python scripts/seed_demo_data.py
cd backend && pip install -r requirements.txt
cd ../frontend && npm install
```

## Docker Quick Start

```bash
docker compose up --build
```

Then visit:

- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- API docs: http://localhost:8000/docs

## Local Development

Backend:

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

## API Documentation

Swagger/OpenAPI is available at:

- http://localhost:8000/docs
- http://localhost:8000/redoc

## Example API Request

```bash
curl -X POST http://localhost:8000/api/v1/analyze \
  -H 'Content-Type: application/json' \
  -d '{"text":"Escalating geopolitical tensions disrupt critical energy supply routes, raising concerns over global inflation and corporate input costs.","source_name":"Yahoo Finance RSS","source_type":"rss"}'
```

## Example API Response

```json
{
  "event_id": "evt_0001",
  "source": {"type": "rss", "name": "Yahoo Finance RSS"},
  "text": "Escalating geopolitical tensions disrupt critical energy supply routes, raising concerns over global inflation and corporate input costs.",
  "sentiment": {"label": "negative", "score": -0.78},
  "event": {"class": "Geopolitical", "confidence": 0.91},
  "impact": {"score": 8.7, "risk_level": "HIGH"},
  "confidence_score": 0.9,
  "risk_trajectory": "ACCELERATING",
  "explanation": [
    "Strong negative financial sentiment",
    "High-severity Geopolitical event",
    "Material exposure detected"
  ],
  "stress_test": {"triggered": true, "scenario": "GEOPOLITICAL_SHOCK"}
}
```

## Dashboard Screenshots

The live dashboard is implemented in the React frontend and shows:

- KPI cards
- live event feed
- risk trajectory chart
- portfolio exposure panel
- stress trigger summary

## Model Evaluation

The heuristic evaluation is documented in docs/model_evaluation.md and the script in scripts/evaluate_models.py.

## Results

This hackathon prototype demonstrates the end-to-end flow required by the challenge:

- Multi-source ingestion
- Financial NLP analysis
- Structured risk output
- Dashboard and WebSocket delivery
- Stress test trigger and portfolio impact calculation

## Domain Impact

This prototype can support sales teams, risk analysts, and portfolio managers by surfacing early warning signals from unstructured financial text and helping prioritize stress testing scenarios.

## Limitations

- Heuristic NLP is not a production-grade bank risk model.
- The platform does not use a real pre-trained FinBERT deployment due the local container constraints for this demo.
- The data is synthetic or locally demo-based unless a live RSS feed is available.
- Stress scenarios are illustrative, not regulatory capital models.

## Future Work

- Replace heuristic scoring with a fine-tuned transformer pipeline
- Add PostgreSQL persistence and Alembic migrations
- Expand entity resolution and source weighting
- Add stronger novelty and clustering using embeddings
- Connect real-time market data and live feeds

## Demo Walkthrough

1. Open the dashboard on http://localhost:3000
2. Observe the live risk overview and the active high-risk event feed
3. Trigger the demo flow or run the sample analysis endpoint
4. Review the sentiment, event class, impact, confidence, and explanation
5. Confirm the stress test triggers and the portfolio value changes

---

This system is a research/prototype risk-intelligence framework for demonstration purposes. Risk scores and stress scenarios are illustrative and are not investment advice, regulatory capital calculations, or production banking risk models.
