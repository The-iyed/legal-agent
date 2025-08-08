import json
import logging
from typing import Any, Optional

import redis

from app.core.config.settings import get_settings

logger = logging.getLogger(__name__)


class RedisCache:
    """Thin wrapper around redis-py for JSON values with TTL."""

    def __init__(self):
        settings = get_settings()
        self._url = settings.REDIS_URL
        self._client: Optional[redis.Redis] = None
        try:
            self._client = redis.from_url(self._url, decode_responses=True)
            # Smoke test
            self._client.ping()
            logger.info(f"Connected to Redis at {self._url}")
        except Exception as e:
            logger.warning(f"Redis unavailable ({self._url}): {e}. Falling back to no-op cache.")
            self._client = None

    def get_json(self, key: str) -> Optional[dict[str, Any]]:
        try:
            if not self._client:
                return None
            raw = self._client.get(key)
            if not raw:
                return None
            return json.loads(raw)
        except Exception as e:
            logger.error(f"Redis GET error for key {key}: {e}")
            return None

    def set_json(self, key: str, value: dict[str, Any], ttl_seconds: int = 86400) -> bool:
        try:
            if not self._client:
                return False
            payload = json.dumps(value)
            self._client.set(key, payload, ex=ttl_seconds)
            return True
        except Exception as e:
            logger.error(f"Redis SET error for key {key}: {e}")
            return False 