"""Structured doctype and field gaps for Step 3."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

from containers.implementation.data_readiness_agent.models import DoctypeGap
from containers.implementation.is_common.gap_report import make_gap_item
from containers.implementation.readiness.inputs import ReadinessInputs
from containers.implementation.readiness.models import FieldGap


def _criticality_to_tier(criticality: str) -> str:
    if criticality == "critical":
        return "critical"
    if criticality == "non_critical":
        return "important"
    return "info"


def build_doctype_gaps(
    pre_analysis: Dict[str, Any],
    *,
    deferred_doctypes: Optional[Set[str]] = None,
) -> List[DoctypeGap]:
    deferred = deferred_doctypes or set()
    gaps: List[DoctypeGap] = []
    for bucket_key, default_crit in (
        ("missing_doctypes", "critical"),
        ("partial_doctypes", "non_critical"),
    ):
        for entry in pre_analysis.get(bucket_key) or []:
            if not isinstance(entry, dict):
                continue
            doctype = str(entry.get("doctype") or "")
            if doctype in deferred:
                continue
            crit = str(entry.get("criticality") or default_crit)
            gaps.append(
                DoctypeGap(
                    doctype=doctype,
                    criticality=crit if crit in ("critical", "non_critical", "optional") else default_crit,  # type: ignore[arg-type]
                    reason=str(entry.get("reason") or entry.get("coverage_note") or "Insufficient file coverage"),
                    missing_fields=list(entry.get("missing_required_fields") or entry.get("blocking_fields") or []),
                    recommendation=str(
                        entry.get("recommendation")
                        or f"Upload a file with columns for {doctype} or confirm deferral"
                    ),
                    can_proceed_without=bool(entry.get("can_proceed_without")),
                )
            )
    return gaps


def build_field_gaps(pre_analysis: Dict[str, Any]) -> List[FieldGap]:
    gaps: List[FieldGap] = []
    seen: Set[tuple] = set()
    for bucket in ("partial_doctypes", "missing_doctypes", "ready_doctypes"):
        for entry in pre_analysis.get(bucket) or []:
            if not isinstance(entry, dict):
                continue
            doctype = str(entry.get("doctype") or "")
            source_file = entry.get("source_file")
            blocking = list(entry.get("blocking_fields") or entry.get("missing_required_fields") or [])
            for field in blocking:
                key = (doctype, field, source_file)
                if key in seen:
                    continue
                seen.add(key)
                gaps.append(
                    FieldGap(
                        doctype=doctype,
                        field=str(field),
                        source_file=source_file,
                        tier="critical",
                        reason=f"Required field {field} not evidenced in uploaded columns",
                    )
                )
    return gaps


def build_gap_items(
    doctype_gaps: List[DoctypeGap],
    field_gaps: List[FieldGap],
    *,
    deferred_doctypes: Optional[Set[str]] = None,
) -> List[Dict[str, Any]]:
    deferred = deferred_doctypes or set()
    items: List[Dict[str, Any]] = []
    for gap in doctype_gaps:
        if gap.doctype in deferred:
            continue
        tier = _criticality_to_tier(gap.criticality)
        severity = "blocking" if tier == "critical" and not gap.can_proceed_without else "choice"
        items.append(
            make_gap_item(
                field=gap.doctype,
                question=gap.recommendation or gap.reason,
                doctype=gap.doctype,
                severity=severity,  # type: ignore[arg-type]
                tier=tier,  # type: ignore[arg-type]
                resolution="upload" if tier == "critical" else "defer_import",
                missing_fields=gap.missing_fields,
            ).to_dict()
        )
    for gap in field_gaps:
        if gap.doctype in deferred:
            continue
        items.append(
            make_gap_item(
                field=gap.field,
                question=gap.reason or f"Which column maps to {gap.field}?",
                doctype=gap.doctype,
                severity="blocking" if gap.tier == "critical" else "choice",  # type: ignore[arg-type]
                tier=gap.tier,  # type: ignore[arg-type]
                source_file=gap.source_file,
                missing_fields=[gap.field],
            ).to_dict()
        )
    return items


def collect_gaps(
    inputs: ReadinessInputs,
    pre_analysis: Dict[str, Any],
) -> tuple[List[DoctypeGap], List[FieldGap], List[Dict[str, Any]]]:
    deferred = set(inputs.target_structure.get("deferred_doctypes") or [])
    doctype_gaps = build_doctype_gaps(pre_analysis, deferred_doctypes=deferred)
    field_gaps = build_field_gaps(pre_analysis)
    gap_items = build_gap_items(doctype_gaps, field_gaps, deferred_doctypes=deferred)
    return doctype_gaps, field_gaps, gap_items
