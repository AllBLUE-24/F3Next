"""Minimal async-friendly circuit breaker (per adapter instance)."""

from __future__ import annotations

import logging
import time
from typing import Awaitable, Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class AsyncCircuitBreaker:
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_seconds: float = 60.0,
    ) -> None:
        self._name = name
        self._failure_threshold = failure_threshold
        self._recovery_seconds = recovery_seconds
        self._failures = 0
        self._open_until = 0.0

    async def call(self, fn: Callable[[], Awaitable[T]]) -> T:
        now = time.monotonic()
        if now < self._open_until:
            logger.warning("Circuit %s open — rejecting call", self._name)
            raise RuntimeError(f"CircuitOpen:{self._name}")

        try:
            out = await fn()
        except Exception:
            self._failures += 1
            if self._failures >= self._failure_threshold:
                self._open_until = time.monotonic() + self._recovery_seconds
                logger.error(
                    "Circuit %s tripped after %d failures — open for %.0fs",
                    self._name,
                    self._failures,
                    self._recovery_seconds,
                )
            raise

        self._failures = 0
        return out
