"""
Async Redis caching layer with TTL support.

Caches:
- Token lists: 30s TTL
- Token details: 60s TTL
- Surge alerts: 5s TTL
- Dune results: 5min TTL
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, Tuple

from redis.asyncio import Redis

logger = logging.getLogger(__name__)

# Default TTLs (seconds)
TTL_TOKEN_LIST = 30
TTL_TOKEN_DETAIL = 60
TTL_SURGE_ALERTS = 5
TTL_DUNE = 300


class CacheClient:
    """Async Redis client wrapper with automatic serialization."""

    def __init__(self, url: str = "redis://redis:6379/0") -> None:
        self.url = url
        self._redis: Optional[Redis] = None
        self._connected = False

    async def connect(self) -> None:
        """Connect to Redis."""
        try:
            self._redis = Redis.from_url(self.url, decode_responses=True)
            await self._redis.ping()
            self._connected = True
            logger.info("Redis connected to %s", self.url)
        except Exception as exc:
            logger.warning("Redis connection failed: %s", exc)
            self._connected = False

    async def close(self) -> None:
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
            self._connected = False

    @property
    def connected(self) -> bool:
        return self._connected

    async def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        """Set a key with optional TTL. Serializes values to JSON."""
        if not self._connected or not self._redis:
            return False
        try:
            serialized = json.dumps(value, default=str)
            if ttl:
                await self._redis.setex(key, ttl, serialized)
            else:
                await self._redis.set(key, serialized)
            return True
        except Exception as exc:
            logger.error("Redis set error for %s: %s", key, exc)
            return False

    async def get(self, key: str) -> Any:
        """Get a key. Returns deserialized value or None."""
        if not self._connected or not self._redis:
            return None
        try:
            data = await self._redis.get(key)
            if data is None:
                return None
            try:
                return json.loads(data)
            except (json.JSONDecodeError, TypeError):
                return data
        except Exception as exc:
            logger.error("Redis get error for %s: %s", key, exc)
            return None

    async def delete(self, key: str) -> bool:
        """Delete a key."""
        if not self._connected or not self._redis:
            return False
        try:
            await self._redis.delete(key)
            return True
        except Exception as exc:
            logger.error("Redis delete error for %s: %s", key, exc)
            return False

    async def set_many(self, mapping: Dict[str, Tuple[str, int | None]]) -> int:
        """Set multiple keys. mapping = {key: (value, ttl|None)}. Returns count of successful sets."""
        if not self._connected or not self._redis:
            return 0
        try:
            pipe = self._redis.pipeline()
            for key, (value, ttl) in mapping.items():
                serialized = json.dumps(value, default=str)
                if ttl:
                    pipe.setex(key, ttl, serialized)
                else:
                    pipe.set(key, serialized)
            await pipe.execute()
            return len(mapping)
        except Exception as exc:
            logger.error("Redis set_many error: %s", exc)
            return 0

    async def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple keys. Returns dict of key -> value."""
        if not self._connected or not self._redis:
            return {}
        try:
            values = await self._redis.mget(keys)
            result = {}
            for key, val in zip(keys, values):
                if val is not None:
                    try:
                        result[key] = json.loads(val)
                    except (json.JSONDecodeError, TypeError):
                        result[key] = val
            return result
        except Exception as exc:
            logger.error("Redis get_many error: %s", exc)
            return {}

    # -- Key templates --

    @staticmethod
    def token_list_key() -> str:
        return "vss:cache:tokens:list"

    @staticmethod
    def token_detail_key(address: str) -> str:
        return f"vss:cache:tokens:{address}:detail"

    @staticmethod
    def surge_alerts_key() -> str:
        return "vss:cache:surges:active"

    @staticmethod
    def new_tokens_key(hours: int = 24) -> str:
        return f"vss:cache:tokens:new:{hours}h"

    @staticmethod
    def dune_query_key(query_id: int) -> str:
        return f"vss:cache:dune:query:{query_id}"


async def get_cache(url: str = "redis://redis:6379/0") -> CacheClient:
    """Get a fresh CacheClient instance and connect it."""
    cache = CacheClient(url)
    await cache.connect()
    return cache
