"""Unified gap consumption for supervisor prompts (readiness + mapping + validate)."""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from containers.implementation.is_common.gap_report import open_critical_gaps


def collect_gap_items(
    *,
    gap_report: Dict[str, Any] | None = None,
    assessment: Dict[str, Any] | None = None,
    preflight_blocks: List[Dict[str, Any]] | None = None,
) -> List[Dict[str, Any]]:
    """Merge gap_items from gap_report, assessment, and mapping preflight."""
    report = gap_report or {}
    items: List[Dict[str, Any]] = list(report.get("gap_items") or [])
    items.extend(report.get("complete_gaps") or [])

    assess = assessment or {}
    nested_report = assess.get("gap_report") or {}
    if nested_report and nested_report is not report:
        items.extend(nested_report.get("gap_items") or [])
        items.extend(nested_report.get("complete_gaps") or [])

    for block in preflight_blocks or []:
        if not isinstance(block, dict):
            continue
        from containers.implementation.is_common.gap_report import gap_from_preflight_block

        items.append(gap_from_preflight_block(block).to_dict())

    # Dedupe
    seen: set[tuple[str, str, str]] = set()
    out: List[Dict[str, Any]] = []
    for raw in items:
        if not isinstance(raw, dict):
            continue
        meta = raw.get("metadata") or {}
        key = (
            str(meta.get("origin") or ""),
            str(raw.get("doctype") or ""),
            str(raw.get("field") or ""),
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(raw)
    return out


def partition_gaps_for_supervisor(
    gap_items: List[Dict[str, Any]],
    *,
    missing_doctypes: List[Dict[str, Any]] | None = None,
    partial_doctypes: List[Dict[str, Any]] | None = None,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Returns (critical_gaps, important_gaps, ler_info_gaps).
    Corpus gaps from assessment merge with unified gap_items.
    """
    critical = [
        g for g in (missing_doctypes or [])
        if str(g.get("criticality", "")).lower() == "critical"
        and not bool(g.get("can_proceed_without", False))
    ]
    important = [
        g for g in (partial_doctypes or [])
        if str(g.get("criticality", "")).lower() in ("non_critical", "important")
        and not bool(g.get("can_proceed_without", True))
    ]

    for item in gap_items:
        meta = item.get("metadata") or {}
        tier = str(meta.get("tier", "")).lower()
        origin = str(meta.get("origin", "")).lower()
        if tier == "info" or str(item.get("severity", "")).lower() == "hint":
            continue
        if tier == "important":
            important.append({
                "doctype": item.get("doctype") or item.get("field"),
                "reason": item.get("question") or "",
                "missing_fields": meta.get("missing_fields") or [],
                "source": origin,
            })
        elif tier == "critical" or str(item.get("severity", "")).lower() == "blocking":
            critical.append({
                "doctype": item.get("doctype") or item.get("field"),
                "reason": item.get("question") or "",
                "missing_fields": meta.get("missing_fields") or [],
                "source": origin,
            })

    ler_info = [
        g for g in gap_items
        if str((g.get("metadata") or {}).get("origin")) == "ler"
        and str(g.get("severity", "")).lower() == "hint"
    ]

    return critical, important, ler_info


def has_open_blocking_gaps(gap_items: List[Dict[str, Any]]) -> bool:
    return bool(open_critical_gaps(gap_items))
