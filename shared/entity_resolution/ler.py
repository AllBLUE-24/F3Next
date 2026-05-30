"""
LER wrappers around BulkLinkResolver — single import path for IS/OS.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from shared.erp_adapters.base import ERPAdapter
from shared.erp_adapters.link_resolver import (
    BulkLinkResolver,
    ResolutionMap,
    _DOCTYPES_WITHOUT_DISABLED,
    resolve_single,
)
from shared.gate_contracts import utc_now_iso

logger = logging.getLogger(__name__)

BRAIN_VERSION = "1.0.0"


async def fetch_link_cache_for_doctypes(
    adapter: ERPAdapter,
    doctypes: set[str] | list[str],
    *,
    log=None,
) -> dict[str, list[str]]:
    """
    Fetch live ERP ``name`` list per doctype (authority list for validators).
    """
    log = log or logger
    cache: dict[str, list[str]] = {}
    for target_doctype in sorted(set(doctypes)):
        if not target_doctype:
            continue
        known_names: list[str] = []
        try:
            if target_doctype in _DOCTYPES_WITHOUT_DISABLED:
                records = await adapter.list_records(target_doctype, ["name"], limit=2000)
            else:
                records = await adapter.list_records(
                    target_doctype,
                    ["name", "disabled"],
                    filters=[["disabled", "=", 0]],
                )
            known_names = [r["name"] for r in records if r.get("name")]
        except Exception as e:
            log.warning("LER: disabled-filter fetch failed for %s: %s", target_doctype, e)
            try:
                records = await adapter.list_records(target_doctype, ["name"], limit=2000)
                known_names = [r["name"] for r in records if r.get("name")]
            except Exception as e2:
                log.warning("LER: fallback fetch failed for %s: %s", target_doctype, e2)
                known_names = []
        cache[target_doctype] = known_names
    return cache


async def build_link_cache(
    adapter: ERPAdapter,
    link_targets: dict[str, set[str]],
    *,
    preferred_abbr: Optional[str] = None,
    log=None,
) -> dict[str, list[str]]:
    """
    Live ERP name lists for all doctypes referenced in *link_targets* keys.
    """
    return await fetch_link_cache_for_doctypes(
        adapter,
        set(link_targets.keys()),
        log=log,
    )


async def build_resolution_map(
    adapter: ERPAdapter,
    link_targets: dict[str, set[str]],
    *,
    preferred_abbr: Optional[str] = None,
    log=None,
) -> ResolutionMap:
    """Delegate to BulkLinkResolver (IS import preflight uses same path)."""
    return await BulkLinkResolver.build_resolution_map(
        adapter,
        link_targets,
        log=log,
        preferred_abbr=preferred_abbr,
    )


def apply_resolved_to_intent(
    intent: dict[str, Any],
    resolution_map: ResolutionMap,
    *,
    link_field_index: dict[str, str],
) -> dict[str, Any]:
    """
    Rewrite intent entity link values using *resolution_map*.

    *link_field_index* maps entity keys → ERP link doctype
    (e.g. ``customer`` → ``Customer``).
    """
    out = dict(intent)
    entities = dict(out.get("entities") or {})
    if not entities:
        return out

    for entity_key, target_dt in link_field_index.items():
        if not target_dt:
            continue
        raw = entities.get(entity_key)
        if isinstance(raw, str) and raw.strip():
            canonical = resolution_map.get_canonical(target_dt, raw.strip())
            if canonical:
                entities[entity_key] = canonical
        elif entity_key == "items" and isinstance(raw, list):
            for row in raw:
                if not isinstance(row, dict):
                    continue
                for field_name, field_value in list(row.items()):
                    if field_name in ("item_code", "item_name") and isinstance(field_value, str):
                        canonical = resolution_map.get_canonical("Item", field_value.strip())
                        if canonical:
                            row["item_code"] = canonical

    out["entities"] = entities
    out["ler_applied_at"] = utc_now_iso()
    return out
