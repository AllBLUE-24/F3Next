"""UI-safe payloads for Step 4 Validate phase."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from containers.implementation.map_validate.models import MapValidateReport

_LEVEL_LABELS = {
    "pass": "Ready to import",
    "partial": "Review warnings",
    "fail": "Fix errors first",
}


def _sanitize(text: str) -> str:
    cleaned = re.sub(r"\b8c\b|\bstep\s*9\b|\bstep\s*11\b", "", text, flags=re.I)
    cleaned = re.sub(r"\bpreflight\b", "column check", cleaned, flags=re.I)
    return cleaned.strip()


def build_validate_ui_payload(
    preview: Dict[str, Any],
    *,
    offline_report: Optional[MapValidateReport] = None,
) -> Dict[str, Any]:
    """
    Transform validate-preview or offline report for Validate UI banner.

    Prefer persisted preview when available; merge offline_report for harness.
    """
    level = (
        preview.get("validation_overall")
        or (offline_report.validation_level if offline_report else None)
        or "partial"
    )
    if level in ("failed",):
        level = "fail"
    if level in ("passed_with_warnings",):
        level = "partial"

    import_ready = preview.get("import_ready")
    if import_ready is None and offline_report:
        import_ready = offline_report.import_ready

    blocking = preview.get("blocking_unmapped_seeds") or []
    open_gaps = preview.get("open_critical_gaps") or []

    requires_ack = (
        level == "partial"
        or preview.get("requires_acknowledgment") is True
        or (offline_report.requires_acknowledgment if offline_report else False)
    )

    summary_parts: List[str] = []
    if offline_report and offline_report.executive_summary:
        summary_parts.append(_sanitize(offline_report.executive_summary))
    elif level == "pass":
        summary_parts.append("All mapped modules passed validation.")
    elif level == "fail":
        summary_parts.append("Blocking validation errors must be resolved before import.")
    else:
        summary_parts.append("Some modules have warnings — review before confirming.")

    if blocking:
        summary_parts.append(f"Unmapped MVP modules: {', '.join(blocking[:5])}.")
    if open_gaps:
        summary_parts.append(f"{len(open_gaps)} open critical gap(s) from readiness or mapping.")

    map_rows = []
    if offline_report:
        map_rows = [r.model_dump() for r in offline_report.map_results]
    elif preview.get("doctypes"):
        for dt in preview["doctypes"]:
            if isinstance(dt, dict):
                map_rows.append({
                    "doctype": dt.get("doctype"),
                    "filename": dt.get("source_file") or "",
                    "passed": dt.get("validation_status") not in ("fail", "failed"),
                    "record_count": dt.get("total_rows") or 0,
                    "status": dt.get("validation_status"),
                })

    return {
        "validation_level": level,
        "validation_label": _LEVEL_LABELS.get(str(level), "Review required"),
        "executive_summary": " ".join(summary_parts),
        "requires_acknowledgment": requires_ack,
        "import_ready": bool(import_ready) and str(level) != "fail",
        "blocking_unmapped_seeds": blocking,
        "open_critical_gaps": open_gaps,
        "map_results": map_rows,
        "doctypes": preview.get("doctypes") or [],
        "import_preview": preview.get("import_preview") or {},
    }


def build_validate_ui_from_report(report: MapValidateReport) -> Dict[str, Any]:
    return build_validate_ui_payload({}, offline_report=report)
