"""Post-recommend guardrails: validate archetype_id and enrich mvp_focus from KB."""

from __future__ import annotations

import logging
from typing import Any, Optional

from containers.discovery.archetype_registry import get_by_id, list_archetype_ids

logger = logging.getLogger(__name__)

_INVALID_ID_TOKENS = frozenset({"null", "none", "undefined", "n/a", ""})


def normalize_archetype_id(raw: Any) -> Optional[str]:
    """Coerce LLM null-ish values to None."""
    if raw is None:
        return None
    aid = str(raw).strip()
    if aid.lower() in _INVALID_ID_TOKENS:
        return None
    return aid


def apply_recommend_guard(
    recommendation: dict[str, Any],
    *,
    f3iche_id: Optional[str],
) -> dict[str, Any]:
    """
    Validate mvp_focus.archetype_id and copy functional_requirements from KB row.

    Invalid ids are cleared so scoping falls back to signal match.
    """
    out = dict(recommendation)
    focus = dict(out.get("mvp_focus") or {})
    raw_id = focus.get("archetype_id")
    aid = normalize_archetype_id(raw_id)

    guard_notes: list[str] = []
    valid_ids = set(list_archetype_ids(f3iche_id))

    if raw_id is not None and aid is None:
        guard_notes.append(f"cleared invalid archetype_id {raw_id!r}")
        focus["archetype_id"] = None
    elif aid and aid not in valid_ids:
        guard_notes.append(f"cleared unknown archetype_id {aid!r}")
        focus["archetype_id"] = None
        aid = None
    else:
        focus["archetype_id"] = aid

    if aid:
        entry = get_by_id(aid, f3iche_id)
        if entry:
            kb_reqs = entry.get("functional_requirements") or []
            if kb_reqs:
                focus["functional_requirements"] = list(kb_reqs)
                guard_notes.append(f"functional_requirements from KB row {aid!r}")

    out["mvp_focus"] = focus
    if guard_notes:
        out["_recommend_guard"] = guard_notes
        logger.info("Recommend guard: %s", "; ".join(guard_notes))
    return out
