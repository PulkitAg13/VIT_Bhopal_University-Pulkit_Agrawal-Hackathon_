"""WebSocket endpoint and ConnectionManager — single Redis subscriber architecture."""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Union

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.redis_client import get_redis, RISK_EVENTS_CHANNEL

logger = logging.getLogger("finrisk.websocket")

router = APIRouter(tags=["websocket"])


class ConnectionManager:
    """Manages active WebSocket connections and handles broadcasts."""

    def __init__(self) -> None:
        self.active_connections: List[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self.active_connections.append(websocket)
        logger.info("WebSocket client connected. Total connected: %d", len(self.active_connections))

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
        logger.info("WebSocket client disconnected. Total connected: %d", len(self.active_connections))

    async def broadcast(self, message: Union[str, Dict[str, Any]]) -> None:
        """Broadcast an event payload to all currently connected clients."""
        text = json.dumps(message, default=str) if isinstance(message, dict) else message
        async with self._lock:
            disconnected = []
            for ws in self.active_connections:
                try:
                    await ws.send_text(text)
                except Exception:
                    disconnected.append(ws)
            for ws in disconnected:
                if ws in self.active_connections:
                    self.active_connections.remove(ws)


manager = ConnectionManager()


async def start_redis_subscriber_task(conn_manager: ConnectionManager) -> None:
    """Single Redis subscriber task started once at application startup.

    Subscribes to RISK_EVENTS_CHANNEL and fans out messages to all connected clients.
    """
    logger.info("Starting single Redis subscriber background worker...")
    while True:
        client = get_redis()
        if client is None:
            logger.warning("Redis not connected. Waiting 5s before subscriber retry...")
            await asyncio.sleep(5)
            continue

        pubsub = client.pubsub()
        try:
            pubsub.subscribe(RISK_EVENTS_CHANNEL)
            logger.info("Single Redis subscriber subscribed to channel '%s'", RISK_EVENTS_CHANNEL)
            while True:
                # Use to_thread to poll without blocking the asyncio event loop
                message = await asyncio.to_thread(pubsub.get_message, True, 0.5)
                if message and message.get("type") == "message":
                    data = message.get("data")
                    if data:
                        await conn_manager.broadcast(data)
                await asyncio.sleep(0.02)
        except asyncio.CancelledError:
            logger.info("Single Redis subscriber shutting down")
            break
        except Exception as exc:
            logger.warning("Single Redis subscriber loop error: %s. Reconnecting in 3s...", exc)
            await asyncio.sleep(3)
        finally:
            try:
                pubsub.unsubscribe(RISK_EVENTS_CHANNEL)
                pubsub.close()
            except Exception:
                pass


@router.websocket("/ws/risk-events")
async def ws_risk_events(websocket: WebSocket) -> None:
    """Client WebSocket connection endpoint."""
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.debug("WebSocket client disconnected with exception: %s", exc)
    finally:
        await manager.disconnect(websocket)


async def broadcast_to_all(event_data: dict) -> None:
    """Direct broadcast convenience function."""
    await manager.broadcast(event_data)
