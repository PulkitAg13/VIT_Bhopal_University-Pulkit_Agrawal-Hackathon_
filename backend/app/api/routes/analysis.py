"""Analysis endpoint — runs the full NLP + risk pipeline."""
from __future__ import annotations

import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.dependencies import risk_service
from app.core.model_manager import ModelUnavailableError
from app.schemas import AnalyzeRequest, RiskSignalResponse

logger = logging.getLogger("finrisk.analysis")

router = APIRouter(tags=["analysis"])


@router.post("/analyze", response_model=RiskSignalResponse)
def analyze(payload: AnalyzeRequest, db: Session = Depends(get_db)) -> RiskSignalResponse:
    if not payload.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")
    try:
        result = risk_service.analyze(
            text=payload.text,
            source_name=payload.source_name,
            source_type=payload.source_type,
            source_url=payload.source_url,
            db=db,
        )
        return RiskSignalResponse(**result)
    except ModelUnavailableError:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Analysis failed unexpectedly: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Unexpected analysis error occurred.")
