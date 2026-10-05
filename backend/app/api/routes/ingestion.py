"""Ingestion endpoint — fetch from real sources and analyze."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.dependencies import risk_service
from app.services.ingestion.sources import get_source
from app.schemas import IngestRequest

router = APIRouter(tags=["ingestion"])


@router.post("/ingest")
def ingest(payload: IngestRequest, db: Session = Depends(get_db)) -> dict:
    try:
        source = get_source(payload.source, payload.ticker, payload.dataset_name)
        items = source.fetch(max_items=payload.max_items)

        if not items:
            return {"ingested": 0, "source": source.name, "signals": [],
                    "message": "No items fetched from source"}

        signals = []
        for item in items:
            result = risk_service.analyze(
                text=item.text,
                source_name=item.source_name,
                source_type=item.source_type,
                source_url=item.source_url,
                published_at=item.published_at,
                db=db,
            )
            signals.append(result)

        return {
            "ingested": len(signals),
            "source": source.name,
            "signals": signals,
        }
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(exc)}")

