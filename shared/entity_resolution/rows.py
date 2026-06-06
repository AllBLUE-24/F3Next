"""
LER helpers for tabular mapped payloads (IS import + validate).
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from shared.erp_adapters.base import ERPAdapter
from shared.erp_adapters.link_resolver import BulkLinkResolver, ResolutionMap
from shared.entity_resolution.ler import build_resolution_map

logger = logging.getLogger(__name__)


def collect_link_targets_from_rows(
    rows: list[dict[str, Any]],
    effective_link_fields: dict[str, str],
) -> dict[str, set[str]]:
    """Scan mapped rows for link field values (delegates to BulkLinkResolver)."""
    return BulkLinkResolver.collect_link_targets_from_rows(rows, effective_link_fields)


def apply_resolution_map_to_rows(
    rows: list[dict[str, Any]],
    effective_link_fields: dict[str, str],
    resolution_map: ResolutionMap,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Rewrite link fields in rows using a resolution map."""
    return BulkLinkResolver.apply_resolution_map_to_rows(
        rows, effective_link_fields, resolution_map,
    )


async def resolve_rows_for_payload(
    adapter: ERPAdapter,
    payload: dict[str, Any],
    known_link_fields: dict[str, str],
    *,
    preferred_abbr: Optional[str] = None,
    log=None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """
    LER pass on one mapped payload dict (mutates records in returned copy).

    Returns ``(updated_payload, summary)`` with corrections and unresolvable_values.
    """
    log = log or logger
    rows = list(payload.get("records") or [])
    if not rows:
        return payload, {"resolved_count": 0, "corrections": [], "unresolvable_values": []}

    effective = {**known_link_fields, **(payload.get("link_fields") or {})}
    targets = collect_link_targets_from_rows(rows, effective)
    if not targets:
        return payload, {"resolved_count": 0, "corrections": [], "unresolvable_values": []}

    resolution_map = await build_resolution_map(
        adapter, targets, preferred_abbr=preferred_abbr, log=log,
    )
    rewritten, summary = apply_resolution_map_to_rows(rows, effective, resolution_map)
    out = dict(payload)
    out["records"] = rewritten
    summary["link_targets"] = {k: sorted(v) for k, v in targets.items()}
    return out, summary


async def resolve_all_mapped_payloads(
    adapter: ERPAdapter,
    mapped_data: dict[str, dict[str, Any]],
    *,
    known_link_fields: Optional[dict[str, str]] = None,
    preferred_abbr: Optional[str] = None,
    log=None,
) -> dict[str, Any]:
    """
    Run LER on every doctype entry in *mapped_data* (in-place update of dict values).

    Returns aggregate report: corrections, unresolvable, per_doctype summaries.
    """
    log = log or logger
    known_link_fields = known_link_fields or {}
    aggregate: dict[str, Any] = {
        "corrections": [],
        "unresolvable_values": [],
        "per_doctype": {},
    }

    for doctype, payload in mapped_data.items():
        if not isinstance(payload, dict):
            continue
        updated, summary = await resolve_rows_for_payload(
            adapter,
            payload,
            known_link_fields,
            preferred_abbr=preferred_abbr,
            log=log,
        )
        mapped_data[doctype] = updated
        aggregate["per_doctype"][doctype] = summary
        aggregate["corrections"].extend(summary.get("corrections") or [])
        for hit in summary.get("unresolvable_values") or []:
            if isinstance(hit, dict) and not hit.get("doctype"):
                tagged = dict(hit)
                tagged["doctype"] = doctype
                aggregate["unresolvable_values"].append(tagged)
            else:
                aggregate["unresolvable_values"].append(hit)

    return aggregate
