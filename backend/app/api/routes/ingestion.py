"""Ingestion endpoint — fetch from real sources and analyze."""
from __future__ import annotations

import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.dependencies import risk_service
from app.core.model_manager import ModelUnavailableError
from app.services.ingestion.sources import get_source
from app.schemas import IngestRequest, IngestResponse

logger = logging.getLogger("finrisk.ingestion")

router = APIRouter(tags=["ingestion"])


@router.post("/ingest", response_model=IngestResponse)
def ingest(payload: IngestRequest, db: Session = Depends(get_db)) -> IngestResponse:
    try:
        source = get_source(payload.source, payload.ticker, payload.dataset_name)
        items = source.fetch(max_items=payload.max_items)

        if not items:
            return IngestResponse(
                ingested=0,
                source=source.name,
                signals=[],
            )

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

        return IngestResponse(
            ingested=len(signals),
            source=source.name,
            signals=signals,
        )
    except ModelUnavailableError:
        raise
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Ingestion failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal ingestion failure.")
