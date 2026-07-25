"""GREEN / YELLOW / RED readiness gate."""
from __future__ import annotations

from typing import Any, Dict, List

from containers.implementation.readiness.models import (
    DoctypeGap,
    FieldGap,
    ReadinessLevel,
    ReadinessMatrix,
)


def compute_readiness_level(
    *,
    matrix: ReadinessMatrix,
    doctype_gaps: List[DoctypeGap],
    field_gaps: List[FieldGap],
    pre_analysis: Dict[str, Any],
    gap_items: List[Dict[str, Any]],
) -> ReadinessLevel:
    summary = pre_analysis.get("summary") or {}
    if summary.get("minimum_viable_possible") is False:
        return "red"

    blocking_items = [
        g for g in gap_items
        if (g.get("severity") or "blocking") == "blocking"
        and (g.get("metadata") or {}).get("tier") == "critical"
    ]
    n_blocking_missing = int(summary.get("n_blocking_missing") or 0)
    n_blocking_partial = int(summary.get("n_blocking_partial") or 0)
    if n_blocking_missing > 0 or n_blocking_partial > 0:
        return "red"
    if blocking_items and summary.get("minimum_viable_possible") is not True:
        return "red"

    partial = pre_analysis.get("partial_doctypes") or []
    assumptions = any(
        bool(r.assumed_fields) or r.status == "partial"
        for r in matrix.rows
    )
    if field_gaps or partial or assumptions:
        return "yellow"

    ready_count = len(pre_analysis.get("ready_doctypes") or [])
    scope_count = len(pre_analysis.get("scope_doctypes") or summary.get("total_required") or 0)
    if scope_count and ready_count >= scope_count:
        return "green"
    if ready_count > 0 and summary.get("minimum_viable_possible") is True:
        return "yellow"
    if ready_count > 0:
        return "yellow"
    return "red"


def gate_summary(level: ReadinessLevel, gap_items: List[Dict[str, Any]]) -> str:
    blocking = sum(
        1 for g in gap_items
        if (g.get("severity") or "blocking") == "blocking"
    )
    if level == "green":
        return "Your uploads cover the agreed Day-1 scope. You can continue to mapping."
    if level == "yellow":
        return (
            f"Most scope is covered; {blocking} item(s) may need confirmation or assumptions at mapping."
        )
    return f"{blocking} blocking gap(s) must be resolved before mapping."
