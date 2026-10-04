from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.ingestion.sources import DemoSource, RSSNewsSource
from app.api.dependencies import risk_service

router = APIRouter(tags=["ingestion"])


class IngestRequest(BaseModel):
    source: str = "demo"
    ticker: str = "AAPL"
    text: str | None = None


@router.post("/ingest")
def ingest(payload: IngestRequest) -> dict:
    source = DemoSource("data/sample/demo_events.json") if payload.source == "demo" else RSSNewsSource(payload.ticker)
    texts = source.fetch()
    if payload.text:
        texts = [payload.text]
    signals = [risk_service.analyze(text, source.name, source.source_type) for text in texts]
    return {"ingested": len(signals), "signals": signals}
