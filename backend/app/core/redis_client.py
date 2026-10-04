from __future__ import annotations

import json
import logging
from typing import Any, Optional

import redis

from app.core.config import get_settings

logger = logging.getLogger("finrisk.redis")

_redis_client: Optional[redis.Redis] = None
RISK_EVENTS_CHANNEL = "risk_events"


def get_redis() -> Optional[redis.Redis]:
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    try:
        settings = get_settings()
        _redis_client = redis.from_url(settings.redis_url, decode_responses=True)
        _redis_client.ping()
        logger.info("Redis connected: %s", settings.redis_url)
        return _redis_client
    except Exception as exc:
        logger.warning("Redis unavailable: %s", exc)
        return None


def publish_event(event_data: dict[str, Any]) -> bool:
    """Publish a risk event to the Redis channel."""
    client = get_redis()
    if client is None:
        return False
    try:
        client.publish(RISK_EVENTS_CHANNEL, json.dumps(event_data, default=str))
        return True
    except Exception as exc:
        logger.warning("Redis publish failed: %s", exc)
        return False


def redis_health() -> dict[str, str]:
    """Check Redis health."""
    client = get_redis()
    if client is None:
        return {"status": "unavailable", "info": "Cannot connect"}
    try:
        client.ping()
        return {"status": "connected"}
    except Exception as exc:
        return {"status": "error", "info": str(exc)}
