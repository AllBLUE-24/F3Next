"""Prometheus metrics for the Context Engine (no-op if prometheus_client missing)."""

from __future__ import annotations

try:
    from prometheus_client import Counter, Histogram

    CONTEXT_ENGINE_REQUESTS = Counter(
        "context_engine_requests_total",
        "Context engine get_context calls",
        ["result"],
    )
    CONTEXT_ENGINE_LATENCY = Histogram(
        "context_engine_load_seconds",
        "Time to assemble project context",
        buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
    )
    CONTEXT_CACHE_HITS = Counter(
        "context_engine_cache_total",
        "Context engine cache tier hits",
        ["tier"],
    )
except ImportError:  # pragma: no cover
    CONTEXT_ENGINE_REQUESTS = None
    CONTEXT_ENGINE_LATENCY = None
    CONTEXT_CACHE_HITS = None


def observe_cache_hit(tier: str) -> None:
    if CONTEXT_CACHE_HITS is not None:
        CONTEXT_CACHE_HITS.labels(tier=tier).inc()
