from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.api.dependencies import risk_service

router = APIRouter(tags=["events"])


@router.get("/events")
def list_events() -> dict:
    return {"items": risk_service.history, "count": len(risk_service.history)}


@router.get("/events/{event_id}")
def get_event(event_id: str) -> dict:
    for evt in risk_service.history:
        if evt["event_id"] == event_id:
            return evt
    raise HTTPException(status_code=404, detail="Event not found")
