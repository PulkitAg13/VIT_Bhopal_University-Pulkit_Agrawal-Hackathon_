from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.api.dependencies import risk_service

router = APIRouter(tags=["analysis"])


class AnalyzeRequest(BaseModel):
    text: str
    source_name: str = "Yahoo Finance RSS"
    source_type: str = "rss"


@router.post("/analyze")
def analyze(payload: AnalyzeRequest) -> dict:
    if not payload.text.strip():
        raise ValueError("Text cannot be empty")
    result = risk_service.analyze(payload.text, payload.source_name, payload.source_type)
    return result
