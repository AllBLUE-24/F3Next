"""Orchestrate Step 3 readiness assessment."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from containers.implementation.data_readiness_agent.models import (
    AssumedField,
    DoctypeGap,
    DoctypeReady,
)
from containers.implementation.readiness.gaps import collect_gaps
from containers.implementation.readiness.inputs import ReadinessInputs
from containers.implementation.readiness.matrix import build_readiness_matrix
from containers.implementation.readiness.models import ReadinessReport
from containers.implementation.readiness.readiness_gate import compute_readiness_level, gate_summary


def _to_doctype_ready(entry: Dict[str, Any]) -> DoctypeReady:
    assumed = [
        AssumedField(**a) if isinstance(a, dict) else a
        for a in (entry.get("assumed_fields") or [])
    ]
    return DoctypeReady(
        doctype=str(entry.get("doctype") or ""),
        source_file=str(entry.get("source_file") or ""),
        coverage_pct=float(entry.get("coverage_pct") or 0.0),
        mapped_fields=list(entry.get("mapped_fields") or []),
        missing_optional_fields=list(entry.get("missing_optional_fields") or []),
        ready_with_assumptions=bool(entry.get("ready_with_assumptions")),
        assumed_fields=assumed,
        evidence_type=entry.get("evidence_type"),
        coverage_note=entry.get("coverage_note"),
    )


def _to_doctype_gap(entry: Dict[str, Any], *, default_crit: str = "critical") -> DoctypeGap:
    crit = str(entry.get("criticality") or default_crit)
    if crit not in ("critical", "non_critical", "optional"):
        crit = default_crit
    return DoctypeGap(
        doctype=str(entry.get("doctype") or ""),
        criticality=crit,  # type: ignore[arg-type]
        reason=str(entry.get("reason") or entry.get("coverage_note") or "Gap detected"),
        missing_fields=list(entry.get("missing_required_fields") or entry.get("blocking_fields") or []),
        recommendation=str(entry.get("recommendation") or "Upload additional data or confirm deferral"),
        can_proceed_without=bool(entry.get("can_proceed_without")),
    )


def assess_readiness(inputs: ReadinessInputs) -> ReadinessReport:
    """Deterministic Step 3 assess — matrix, gaps, and gate without LLM."""
    matrix, pre_analysis, schema_sources = build_readiness_matrix(inputs)
    _, field_gaps, gap_items = collect_gaps(inputs, pre_analysis)
    doctype_gaps = [
        _to_doctype_gap(e, default_crit="critical")
        for e in (pre_analysis.get("missing_doctypes") or [])
    ]
    partial_gaps = [
        _to_doctype_gap(e, default_crit="non_critical")
        for e in (pre_analysis.get("partial_doctypes") or [])
    ]
    level = compute_readiness_level(
        matrix=matrix,
        doctype_gaps=doctype_gaps + partial_gaps,
        field_gaps=field_gaps,
        pre_analysis=pre_analysis,
        gap_items=gap_items,
    )
    summary = pre_analysis.get("summary") or {}
    mvp_possible = summary.get("minimum_viable_possible")
    if mvp_possible is None:
        mvp_possible = level != "red"
    ready = [_to_doctype_ready(e) for e in (pre_analysis.get("ready_doctypes") or [])]
    missing = doctype_gaps
    partial = partial_gaps
    blocking_count = sum(1 for g in gap_items if (g.get("severity") or "") == "blocking")
    score = pre_analysis.get("import_readiness_score")
    if score is None:
        scope_n = max(len(pre_analysis.get("scope_doctypes") or []), 1)
        score = round(len(ready) / scope_n, 3)
        if level == "red":
            score = min(float(score), 0.49)
        elif level == "yellow":
            score = min(float(score), 0.85)

    return ReadinessReport(
        ready_doctypes=ready,
        partial_doctypes=partial,
        missing_doctypes=missing,
        gap_report={"gap_items": gap_items, "matrix_summary": matrix.summary},
        minimum_viable_import_possible=bool(mvp_possible),
        user_action_required=level != "green",
        executive_summary=gate_summary(level, gap_items),
        import_readiness_score=float(score or 0.0),
        matrix=matrix,
        readiness_level=level,
        field_gaps=field_gaps,
        gap_items=gap_items,
        schema_sources=schema_sources,
        pre_analysis=pre_analysis,
    )
