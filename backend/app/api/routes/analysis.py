"""Analysis endpoint — runs the full NLP + risk pipeline."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.dependencies import risk_service
from app.schemas import AnalyzeRequest

router = APIRouter(tags=["analysis"])


@router.post("/analyze")
def analyze(payload: AnalyzeRequest, db: Session = Depends(get_db)) -> dict:
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
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(exc)}")
