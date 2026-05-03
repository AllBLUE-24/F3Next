"""L1 in-process TTL cache + optional L2 Redis."""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Optional

from shared.context_engine.config import L1_MAX_SIZE, L1_TTL_SEC, L2_TTL_SEC, REDIS_URL

logger = logging.getLogger(__name__)


class _L1Entry:
    __slots__ = ("value", "expires_at")

    def __init__(self, value: Any, ttl_sec: int) -> None:
        self.value = value
        self.expires_at = time.monotonic() + ttl_sec


class ContextCache:
    """Two-tier cache: L1 memory (LRU-ish by max size) + L2 Redis JSON."""

    def __init__(self) -> None:
        self._l1: dict[str, _L1Entry] = {}
        self._l1_order: list[str] = []
        self._l1_max = L1_MAX_SIZE
        self._l1_ttl = L1_TTL_SEC
        self._l2_ttl = L2_TTL_SEC
        self._redis = None
        if REDIS_URL:
            try:
                import redis.asyncio as redis_async

                self._redis = redis_async.from_url(REDIS_URL, decode_responses=True)
            except Exception as e:  # pragma: no cover
                logger.warning("ContextCache: Redis unavailable (%s) — L1 only", e)

    def _l1_touch(self, key: str) -> None:
        try:
            self._l1_order.remove(key)
        except ValueError:
            pass
        self._l1_order.append(key)
        while len(self._l1_order) > self._l1_max:
            oldest = self._l1_order.pop(0)
            self._l1.pop(oldest, None)

    async def get(self, key: str) -> Optional[Any]:
        now = time.monotonic()
        ent = self._l1.get(key)
        if ent and ent.expires_at > now:
            return ent.value
        if ent:
            self._l1.pop(key, None)
            try:
                self._l1_order.remove(key)
            except ValueError:
                pass

        if self._redis is None:
            return None

        try:
            raw = await self._redis.get(f"ce:{key}")
            if raw is None:
                return None
            val = json.loads(raw)
            self._l1_set(key, val)
            return val
        except Exception as e:  # pragma: no cover
            logger.debug("ContextCache L2 get failed: %s", e)
            return None

    def _l1_set(self, key: str, value: Any) -> None:
        self._l1[key] = _L1Entry(value, self._l1_ttl)
        self._l1_touch(key)

    async def set(self, key: str, value: Any) -> None:
        self._l1_set(key, value)
        if self._redis is None:
            return
        try:
            await self._redis.set(
                f"ce:{key}",
                json.dumps(value, default=str),
                ex=self._l2_ttl,
            )
        except Exception as e:  # pragma: no cover
            logger.debug("ContextCache L2 set failed: %s", e)

    async def invalidate_prefix(self, prefix: str) -> None:
        """Invalidate keys starting with prefix (L1 scan + Redis SCAN)."""
        to_del = [k for k in self._l1 if k.startswith(prefix)]
        for k in to_del:
            self._l1.pop(k, None)
            try:
                self._l1_order.remove(k)
            except ValueError:
                pass

        if self._redis is None:
            return
        try:
            cursor = 0
            pattern = f"ce:{prefix}*"
            while True:
                cursor, keys = await self._redis.scan(cursor=cursor, match=pattern, count=100)
                if keys:
                    await self._redis.delete(*keys)
                if cursor == 0:
                    break
        except Exception as e:  # pragma: no cover
            logger.debug("ContextCache L2 invalidate failed: %s", e)
