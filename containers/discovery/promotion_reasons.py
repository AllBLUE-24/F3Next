"""Parse validator promotion notes into doctype → reason map for UI transparency."""

from __future__ import annotations

import re

from containers.discovery.archetype_registry import canonicalize_seed

_PROMOTED_RE = re.compile(
    r"^Promoted\s+(.+?)\s+[—–-]\s+(.+)$",
    re.IGNORECASE,
)


def promotion_reasons_from_notes(notes: list[str]) -> dict[str, str]:
    """Extract per-doctype promotion reasons from validator note lines."""
    reasons: dict[str, str] = {}
    for note in notes or []:
        text = (note or "").strip()
        match = _PROMOTED_RE.match(text)
        if not match:
            continue
        dt = canonicalize_seed(match.group(1).strip())
        if dt:
            reasons[dt] = match.group(2).strip()
    return reasons


__all__ = ["promotion_reasons_from_notes"]
