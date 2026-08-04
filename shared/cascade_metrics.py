"""Prometheus metrics for cascade worker (optional dependency)."""

from __future__ import annotations

try:
    from prometheus_client import Counter

    CASCADE_EVENTS_RECEIVED_TOTAL = Counter(
        "cascade_events_received_total",
        "Cascade workflows started from ERPNext webhooks",
        ["result"],
    )
    CASCADE_RULES_MATCHED_TOTAL = Counter(
        "cascade_rules_matched_total",
        "Cascade rules matched per doctype/event",
        ["doctype", "trigger_event"],
    )
    CASCADE_NOTIFICATIONS_DISPATCHED_TOTAL = Counter(
        "cascade_notifications_dispatched_total",
        "Notifications written by cascade dispatcher",
        ["channel", "department"],
    )
except ImportError:  # pragma: no cover
    CASCADE_EVENTS_RECEIVED_TOTAL = None
    CASCADE_RULES_MATCHED_TOTAL = None
    CASCADE_NOTIFICATIONS_DISPATCHED_TOTAL = None
