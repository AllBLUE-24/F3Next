"""
Canonical ValidationReport shape for IS validate step.

Single JSON artifact for API, supervisor, and chat — stored in R2 and surfaced via launcher.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def enrich_checks_with_sources(
    report: Dict[str, Any],
    source_files_by_doctype: Dict[str, List[str]],
) -> Dict[str, Any]:
    """Attach source_files[] to each check from merge aggregation."""
    checks = report.get("checks") or []
    if not isinstance(checks, list):
        return report
    for check in checks:
        if not isinstance(check, dict):
            continue
        dt = check.get("doctype")
        if dt:
            check["source_files"] = list(source_files_by_doctype.get(dt) or [])
    report["checks"] = checks
    return report


def normalize_validation_report(raw: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Normalize DB/R2 fragments into canonical ValidationReport dict."""
    if not raw:
        return None

    overall = str(raw.get("overall") or "pass")
    checks_out: List[Dict[str, Any]] = []

    for check in raw.get("checks") or []:
        if not isinstance(check, dict):
            continue
        dt = check.get("doctype") or ""
        status = check.get("status") or check.get("overall_status") or "pass"
        errors = list(check.get("errors") or [])
        warnings = list(check.get("warnings") or [])
        checks_out.append(
            {
                "doctype": dt,
                "status": status,
                "row_count": int(check.get("row_count") or check.get("total_records_checked") or 0),
                "source_files": list(check.get("source_files") or []),
                "errors": errors,
                "warnings": warnings,
                "row_issues": list(check.get("row_issues") or []),
            }
        )

    return {
        "overall": overall,
        "timestamp": raw.get("timestamp"),
        "checks": checks_out,
        "errors": list(raw.get("errors") or []),
        "warnings": list(raw.get("warnings") or []),
        "ler_gaps": list(raw.get("ler_gaps") or []),
        "import_preview": raw.get("import_preview") or {},
    }


def merge_db_checks_with_r2(
    db_checks: List[Dict[str, Any]],
    r2_report: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Prefer R2 full report; fall back to DB-assembled checks."""
    if r2_report:
        return normalize_validation_report(r2_report) or {
            "overall": "pass",
            "checks": [],
            "errors": [],
            "warnings": [],
        }

    overall = "pass"
    for c in db_checks:
        st = c.get("status") or "pass"
        if st in ("fail", "failed"):
            overall = "fail"
        elif st in ("partial", "warning", "passed_with_warnings") and overall == "pass":
            overall = "partial"

    return {
        "overall": overall,
        "checks": db_checks,
        "errors": [],
        "warnings": [],
    }
