from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class CacheValue:
    value_json: str
    expires_at: float


class InMemoryTTLCache:
    def __init__(self) -> None:
        self._store: dict[str, CacheValue] = {}

    async def get(self, key: str) -> Optional[str]:
        v = self._store.get(key)
        if not v:
            return None
        if time.time() >= v.expires_at:
            self._store.pop(key, None)
            return None
        return v.value_json

    async def set(self, key: str, value_json: str, ttl_s: int) -> None:
        self._store[key] = CacheValue(value_json=value_json, expires_at=time.time() + ttl_s)


_DEFAULT_TTL_S = int(os.getenv("RAG_CACHE_TTL_SECONDS", "86400") or "86400")  # 24h
_REDIS_URL = os.getenv("REDIS_URL") or os.getenv("REDIS_DSN")

_mem_cache = InMemoryTTLCache()
_redis = None

if _REDIS_URL:
    try:
        from redis.asyncio import Redis

        _redis = Redis.from_url(_REDIS_URL, decode_responses=True)
        logger.info("RAG cache: using Redis at %s", _REDIS_URL)
    except Exception as e:
        logger.warning("RAG cache: Redis unavailable (%s) — using in-memory cache", e)
        _redis = None


async def cache_get_json(key: str) -> Optional[Any]:
    raw = None
    if _redis is not None:
        try:
            raw = await _redis.get(key)
        except Exception:
            raw = None
    if raw is None:
        raw = await _mem_cache.get(key)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None


async def cache_set_json(key: str, value: Any, ttl_s: int = _DEFAULT_TTL_S) -> None:
    raw = json.dumps(value, ensure_ascii=False)
    if _redis is not None:
        try:
            await _redis.setex(key, ttl_s, raw)
            return
        except Exception:
            pass
    await _mem_cache.set(key, raw, ttl_s)

