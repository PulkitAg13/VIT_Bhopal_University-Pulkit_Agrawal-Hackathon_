"""WebSocket endpoint — broadcasts risk events via Redis pub/sub."""
from __future__ import annotations

import asyncio
import json
import logging
from typing import List

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.redis_client import get_redis, RISK_EVENTS_CHANNEL

logger = logging.getLogger("finrisk.websocket")

router = APIRouter(tags=["websocket"])

_active_connections: List[WebSocket] = []


@router.websocket("/ws/risk-events")
async def ws_risk_events(websocket: WebSocket) -> None:
    await websocket.accept()
    _active_connections.append(websocket)
    logger.info("WebSocket client connected. Total: %d", len(_active_connections))

    # Start Redis subscriber in background
    subscriber_task = asyncio.create_task(_redis_subscriber(websocket))

    try:
        while True:
            # Keep connection alive, handle pings
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.warning("WebSocket error: %s", exc)
    finally:
        subscriber_task.cancel()
        if websocket in _active_connections:
            _active_connections.remove(websocket)
        logger.info("WebSocket client disconnected. Total: %d", len(_active_connections))


async def _redis_subscriber(websocket: WebSocket) -> None:
    """Subscribe to Redis channel and forward events to this WebSocket."""
    client = get_redis()
    if client is None:
        logger.warning("Redis unavailable — WebSocket will rely on direct broadcast")
        # Keep task alive but do nothing
        try:
            while True:
                await asyncio.sleep(60)
        except asyncio.CancelledError:
            return

    pubsub = client.pubsub()
    try:
        pubsub.subscribe(RISK_EVENTS_CHANNEL)
        while True:
            message = pubsub.get_message(ignore_subscribe_messages=True, timeout=0.1)
            if message and message["type"] == "message":
                try:
                    await websocket.send_text(message["data"])
                except Exception:
                    break
            await asyncio.sleep(0.05)
    except asyncio.CancelledError:
        pass
    except Exception as exc:
        logger.warning("Redis subscriber error: %s", exc)
    finally:
        try:
            pubsub.unsubscribe(RISK_EVENTS_CHANNEL)
            pubsub.close()
        except Exception:
            pass


async def broadcast_to_all(event_data: dict) -> None:
    """Broadcast event directly to all connected WebSocket clients."""
    disconnected = []
    for ws in _active_connections:
        try:
            await ws.send_json(event_data)
        except Exception:
            disconnected.append(ws)
    for ws in disconnected:
        _active_connections.remove(ws)
