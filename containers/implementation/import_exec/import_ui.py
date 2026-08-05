"""UI-safe payloads for Step 5 Import phase."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from containers.implementation.import_exec.models import ImportExecutionReport

_LEVEL_LABELS = {
    "success": "Ready to import",
    "partial": "Partial plan",
    "failed": "Nothing to import",
    "blocked": "Import blocked",
}


def _sanitize(text: str) -> str:
    cleaned = re.sub(r"\bstep\s*1[0-3]\b|\bphase_[a-z0-9_]+\b", "", text, flags=re.I)
    cleaned = re.sub(r"\bpreflight\b", "pre-import check", cleaned, flags=re.I)
    return cleaned.strip()


def build_import_ui_payload(
    plan: Optional[Dict[str, Any]] = None,
    import_results: Optional[List[Dict[str, Any]]] = None,
    *,
    offline_report: Optional[ImportExecutionReport] = None,
    stage: Optional[str] = None,
) -> Dict[str, Any]:
    """Transform import plan, results, or offline report for Import UI."""
    if offline_report:
        level = offline_report.import_level
        plan_status = offline_report.plan_status
        import_ready = offline_report.import_ready
        summary = _sanitize(offline_report.executive_summary)
        create_count = offline_report.create_step_count
        data_gaps = offline_report.data_gap_count
        optional_gaps = offline_report.optional_gap_count
        phases = offline_report.phases
        ordered_phases = offline_report.ordered_phase_ids
        steps = [s.model_dump() for s in offline_report.steps]
        blocked_reasons = list(offline_report.blocked_reasons)
    else:
        plan_status = str((plan or {}).get("status") or (plan or {}).get("plan_status") or "blocked")
        phases = (plan or {}).get("phases") or {}
        blocked_reasons = list((plan or {}).get("blocked_reasons") or [])
        create_count = 0
        data_gaps = 0
        optional_gaps = len((plan or {}).get("optional_gaps") or [])
        steps = []
        for phase_id, phase_data in phases.items():
            if isinstance(phase_data, dict):
                for step in phase_data.get("steps") or []:
                    if isinstance(step, dict):
                        action = str(step.get("action") or "")
                        steps.append({
                            "phase_id": phase_id,
                            "doctype": step.get("doctype"),
                            "action": action,
                            "records": step.get("records"),
                        })
                        if action == "create":
                            create_count += 1
                        elif action == "data_gap":
                            data_gaps += 1

        from containers.implementation.import_exec.gate import compute_import_level, compute_import_ready
        from containers.implementation.import_agent.phase_order import sort_phases

        ordered_phases = [pid for pid, _ in sort_phases(phases if isinstance(phases, dict) else {})]
        import_ready = compute_import_ready(
            plan_status if plan_status in ("ready", "ready_with_gaps", "blocked") else "blocked",
            validation_level="partial",
            import_ready_from_validate=True,
            create_step_count=create_count,
            data_gap_count=data_gaps,
        )
        level = compute_import_level(
            plan_status if plan_status in ("ready", "ready_with_gaps", "blocked") else "blocked",
            create_step_count=create_count,
            data_gap_count=data_gaps,
        )
        if stage == "complete_with_errors":
            level = "partial"
        elif stage == "import_blocked":
            level = "blocked"
        summary = ""

    results_summary = _summarize_results(import_results or [])

    if not summary:
        if level == "success":
            summary = f"{create_count} module(s) ready to import in order."
        elif level == "blocked":
            summary = blocked_reasons[0] if blocked_reasons else "Import is blocked."
        elif level == "partial":
            summary = f"{create_count} module(s) ready; review deferred or partial items."
        else:
            summary = "No records are ready to import yet."

    return {
        "import_level": level,
        "import_label": _LEVEL_LABELS.get(str(level), "Review required"),
        "plan_status": plan_status,
        "import_ready": import_ready,
        "executive_summary": summary,
        "create_step_count": create_count,
        "data_gap_count": data_gaps,
        "optional_gap_count": optional_gaps,
        "ordered_phase_ids": ordered_phases,
        "phases": phases,
        "steps": steps,
        "blocked_reasons": blocked_reasons,
        "results_summary": results_summary,
    }


def build_import_ui_from_report(report: ImportExecutionReport) -> Dict[str, Any]:
    return build_import_ui_payload(offline_report=report)


def _summarize_results(rows: List[Dict[str, Any]]) -> Dict[str, int]:
    steps_failed = 0
    steps_succeeded = 0
    records_succeeded = 0
    for row in rows:
        status = str(row.get("status") or "")
        failed = status in ("error", "failed") or int(row.get("records_failed") or 0) > 0
        if failed:
            steps_failed += 1
        elif status in ("success", "ok") or int(row.get("records_succeeded") or 0) > 0:
            steps_succeeded += 1
        records_succeeded += int(row.get("records_succeeded") or 0)
    return {
        "steps_succeeded": steps_succeeded,
        "steps_failed": steps_failed,
        "records_succeeded": records_succeeded,
    }
