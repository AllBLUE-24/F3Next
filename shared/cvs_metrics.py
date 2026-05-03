"""Prometheus metrics for CVS HTTP surface (optional dependency)."""

from __future__ import annotations

try:
    from prometheus_client import Counter

    CVS_WEBHOOKS_TOTAL = Counter(
        "cvs_webhook_requests_total",
        "CVS webhook HTTP handling",
        ["result"],
    )
    CVS_FORCE_SYNC_TOTAL = Counter(
        "cvs_force_sync_requests_total",
        "CVS force-sync API calls",
        ["result"],
    )
except ImportError:  # pragma: no cover
    CVS_WEBHOOKS_TOTAL = None
    CVS_FORCE_SYNC_TOTAL = None
