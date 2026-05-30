"""Expected Company Brain keys in context_snapshots (types contract for os-brain)."""

from __future__ import annotations

from typing import Any

from shared.entity_resolution.ler import BRAIN_VERSION


def brain_snapshot_keys() -> dict[str, str]:
    """Documented JSON keys written by resolve_entities (branch-02)."""
    return {
        "link_cache": "dict[str, list[str]] — live ERP name lists per doctype",
        "resolved_entities": "dict — canonical party/items/company after LER",
        "resolution_gaps": "list[GapItem dicts] — blocking/choice gaps",
        "live_fetched_at": "ISO8601 UTC",
        "brain_version": f"str — current {BRAIN_VERSION}",
    }


def empty_brain_overlay() -> dict[str, Any]:
    """Starter overlay merged into context snapshot."""
    return {
        "link_cache": {},
        "resolved_entities": {},
        "resolution_gaps": [],
        "live_fetched_at": None,
        "brain_version": BRAIN_VERSION,
    }
