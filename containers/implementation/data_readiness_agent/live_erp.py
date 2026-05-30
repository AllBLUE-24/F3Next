"""
Live ERP emptiness checks for IS readiness (LER authority).

Greenfield IS: empty live masters are expected before import. Only block when the
live site is empty *and* uploaded files do not cover that doctype.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Masters checked against live ERP when relevant to the target structure
_LIVE_MASTER_DOCTYPES = ("Customer", "Supplier", "Item", "Company", "Warehouse")


def _normalize_doctype(doctype: str) -> str:
    try:
        from containers.implementation.is_common.doctype_resolver import resolve_doctype

        return resolve_doctype(doctype) or doctype
    except Exception:
        return doctype


def file_covered_doctypes(
    ready_doctypes: list[dict[str, Any]] | None,
    *,
    partial_doctypes: list[dict[str, Any]] | None = None,
    partial_coverage_threshold: float = 0.45,
) -> set[str]:
    """Doctypes the uploaded corpus is ready (or sufficiently partial) to import."""
    covered: set[str] = set()
    for row in ready_doctypes or []:
        dt = row.get("doctype") if isinstance(row, dict) else None
        if dt:
            covered.add(_normalize_doctype(dt))
    for row in partial_doctypes or []:
        dt = row.get("doctype") if isinstance(row, dict) else None
        if not dt:
            continue
        try:
            pct = float(row.get("coverage_pct", 0) or 0)
        except (TypeError, ValueError):
            pct = 0.0
        if pct >= partial_coverage_threshold:
            covered.add(_normalize_doctype(dt))
    return covered


def classify_empty_live_masters(
    empty_doctypes: list[str],
    file_covered: set[str],
) -> tuple[list[str], list[str], list[dict[str, Any]]]:
    """
    Split empty live masters into blocking vs import-will-create.

    Returns:
        live_empty_blocking, live_empty_covered_by_import, complete_gaps
    """
    from shared.gate_contracts import GapItem

    blocking: list[str] = []
    covered_by_import: list[str] = []
    complete_gaps: list[dict[str, Any]] = []

    for dt in sorted(empty_doctypes):
        canon = _normalize_doctype(dt)
        if canon in file_covered:
            covered_by_import.append(dt)
            continue
        blocking.append(dt)
        complete_gaps.append(
            GapItem(
                field=dt,
                doctype=dt,
                question=(
                    f"No {dt} records exist on your live ERP site yet, and we could not "
                    f"find {dt} data in your uploaded files. Upload a file with {dt} data "
                    f"or create records in ERPNext before import."
                ),
                severity="blocking",
                rule_id="is_live_erp_empty",
                metadata={"source": "live_erp", "ler_authority": True},
            ).to_dict()
        )

    return blocking, covered_by_import, complete_gaps


async def assess_live_erp_masters(
    project_id: str,
    required_doctypes: list[str],
    *,
    ready_doctypes: list[dict[str, Any]] | None = None,
    partial_doctypes: list[dict[str, Any]] | None = None,
    log=None,
) -> dict[str, Any]:
    """
    Fetch live ERP name lists and flag empty masters relevant to target structure.

    Returns:
        link_cache, live_empty, live_empty_blocking, live_empty_covered_by_import,
        complete_gaps (GateResult-shaped dicts — blocking only)
    """
    log = log or logger
    from shared.entity_resolution.is_adapter import resolve_is_erp_adapter
    from shared.entity_resolution.ler import fetch_link_cache_for_doctypes

    _, adapter = await resolve_is_erp_adapter(project_id, log=log)
    if not adapter:
        return {
            "skipped": True,
            "link_cache": {},
            "live_empty": [],
            "live_empty_blocking": [],
            "live_empty_covered_by_import": [],
            "complete_gaps": [],
        }

    needed = set(_LIVE_MASTER_DOCTYPES)
    req = set(required_doctypes or [])
    if req & {"Sales Order", "Sales Invoice", "Delivery Note", "Quotation"}:
        needed.add("Customer")
    if req & {"Purchase Order", "Purchase Invoice", "Purchase Receipt"}:
        needed.add("Supplier")
    if req & {"Sales Order", "Purchase Order", "Stock Entry", "BOM", "Work Order"}:
        needed.add("Item")

    link_cache = await fetch_link_cache_for_doctypes(adapter, needed, log=log)
    live_empty: list[str] = []

    for dt in sorted(needed):
        names = link_cache.get(dt) or []
        if not names:
            live_empty.append(dt)

    file_covered = file_covered_doctypes(ready_doctypes, partial_doctypes=partial_doctypes)
    blocking, covered_by_import, complete_gaps = classify_empty_live_masters(
        live_empty, file_covered
    )

    if live_empty:
        log.info(
            "  Live ERP empty masters: all=%s blocking=%s covered_by_import=%s",
            live_empty,
            blocking,
            covered_by_import,
        )

    return {
        "skipped": False,
        "link_cache": link_cache,
        "live_empty": live_empty,
        "live_empty_blocking": blocking,
        "live_empty_covered_by_import": covered_by_import,
        "complete_gaps": complete_gaps,
    }
