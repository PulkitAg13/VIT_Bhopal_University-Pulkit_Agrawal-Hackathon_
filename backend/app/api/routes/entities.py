from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.api.dependencies import risk_service

router = APIRouter(tags=["entities"])


@router.get("/entities")
def list_entities() -> dict:
    items = []
    for evt in risk_service.history:
        for entity in evt["entities"]:
            items.append({"name": entity["name"], "ticker": entity["ticker"], "risk": evt["impact"]["score"]})
    return {"items": items, "count": len(items)}


@router.get("/entities/{entity_id}")
def get_entity(entity_id: str) -> dict:
    for evt in risk_service.history:
        for entity in evt["entities"]:
            if entity.get("name") == entity_id or entity.get("ticker") == entity_id:
                return {"entity": entity, "latest_signal": evt}
    raise HTTPException(status_code=404, detail="Entity not found")
