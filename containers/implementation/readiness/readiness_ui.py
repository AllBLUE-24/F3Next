"""UI-safe payloads for Step 3 Analyze phase — no internal pipeline strings."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from containers.implementation.readiness.models import ReadinessReport

_LEVEL_LABELS = {
    "green": "Ready to map",
    "yellow": "Review before mapping",
    "red": "Upload more data first",
}


def _sanitize(text: str) -> str:
    cleaned = re.sub(r"\b8c\b", "readiness check", text, flags=re.I)
    cleaned = re.sub(r"\bdry_run\b", "preflight", cleaned, flags=re.I)
    cleaned = re.sub(r"\bpreflight\b", "column check", cleaned, flags=re.I)
    return cleaned.strip()


def _matrix_rows_from_report(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    gap_report = report.get("gap_report") or {}
    matrix = gap_report.get("matrix") or report.get("matrix") or {}
    rows = matrix.get("rows") if isinstance(matrix, dict) else None
    if rows:
        return [
            {
                "filename": r.get("filename"),
                "doctype": r.get("doctype"),
                "status": r.get("status"),
                "required_fields": r.get("required_fields") or [],
                "present_fields": r.get("present_fields") or [],
                "missing_fields": r.get("missing_fields") or [],
                "in_mvp_scope": r.get("in_mvp_scope", True),
            }
            for r in rows
            if isinstance(r, dict)
        ]
    # Legacy: synthesize coarse rows from ready/partial/missing lists
    out: List[Dict[str, Any]] = []
    for bucket, status in (
        ("ready_doctypes", "ready"),
        ("partial_doctypes", "partial"),
        ("missing_doctypes", "missing"),
    ):
        for entry in report.get(bucket) or []:
            if not isinstance(entry, dict):
                continue
            out.append({
                "filename": entry.get("source_file") or "",
                "doctype": entry.get("doctype"),
                "status": status,
                "required_fields": entry.get("missing_required_fields") or [],
                "present_fields": entry.get("mapped_fields") or [],
                "missing_fields": entry.get("blocking_fields")
                or entry.get("missing_required_fields")
                or [],
                "in_mvp_scope": True,
            })
    return out


def build_readiness_ui_payload(report: Dict[str, Any]) -> Dict[str, Any]:
    """Transform stored or live readiness report for Analyze UI."""
    gap_report = report.get("gap_report") or {}
    level = (
        report.get("readiness_level")
        or gap_report.get("readiness_level")
        or _level_from_legacy(report)
    )
    summary = _sanitize(str(report.get("executive_summary") or ""))
    return {
        "readiness_level": level,
        "readiness_label": _LEVEL_LABELS.get(level, "Review required"),
        "executive_summary": summary,
        "requires_acknowledgment": level == "yellow",
        "can_continue_to_mapping": level in ("green", "yellow"),
        "minimum_viable_possible": bool(report.get("minimum_viable_import_possible", report.get("minimum_viable_possible"))),
        "import_readiness_score": report.get("import_readiness_score"),
        "matrix": {
            "rows": _matrix_rows_from_report(report),
            "overclaims": (gap_report.get("matrix_summary") or {}).get("overclaims")
            or gap_report.get("corpus_overclaims")
            or [],
        },
        "gap_items": [
            {
                "field": g.get("field"),
                "question": _sanitize(str(g.get("question") or "")),
                "doctype": g.get("doctype"),
                "severity": g.get("severity"),
            }
            for g in (gap_report.get("gap_items") or report.get("gap_items") or [])
            if isinstance(g, dict)
        ],
        "ready_doctypes": [r.get("doctype") for r in (report.get("ready_doctypes") or []) if isinstance(r, dict)],
        "missing_doctypes": [r.get("doctype") for r in (report.get("missing_doctypes") or []) if isinstance(r, dict)],
    }


def build_readiness_ui_payload_from_model(report: ReadinessReport) -> Dict[str, Any]:
    return build_readiness_ui_payload(report.model_dump())


def _level_from_legacy(report: Dict[str, Any]) -> str:
    if report.get("minimum_viable_possible") is False or report.get("minimum_viable_import_possible") is False:
        return "red"
    score = float(report.get("import_readiness_score") or 0.0)
    if score >= 0.9 and not report.get("user_action_required"):
        return "green"
    if score >= 0.5:
        return "yellow"
    return "red"
