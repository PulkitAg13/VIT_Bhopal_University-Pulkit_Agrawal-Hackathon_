from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(tags=["websocket"])

_active_connections: list[WebSocket] = []


@router.websocket("/ws/risk-events")
async def ws_risk_events(websocket: WebSocket) -> None:
    await websocket.accept()
    _active_connections.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        _active_connections.remove(websocket)


def broadcast_event(event: dict) -> None:
    for connection in _active_connections:
        try:
            connection.send_json(event)
        except Exception:
            _active_connections.remove(connection)
