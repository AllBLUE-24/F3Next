"""Import gate for Step 5."""
from __future__ import annotations

from typing import Any, Dict, List

from containers.implementation.import_exec.config import block_on_validation_fail, require_map_validate_gate
from containers.implementation.import_exec.models import ImportLevel, PlanStatus


def compute_import_level(
    plan_status: PlanStatus,
    *,
    create_step_count: int,
    data_gap_count: int,
    execution_steps_failed: int = 0,
) -> ImportLevel:
    if plan_status == "blocked":
        return "blocked"
    if execution_steps_failed > 0:
        return "partial" if create_step_count > 0 else "failed"
    if data_gap_count > 0 and create_step_count == 0:
        return "failed"
    if plan_status == "ready_with_gaps":
        return "partial"
    if create_step_count == 0:
        return "failed"
    return "success"


def compute_import_ready(
    plan_status: PlanStatus,
    *,
    validation_level: str,
    import_ready_from_validate: bool,
    create_step_count: int,
    data_gap_count: int,
) -> bool:
    if require_map_validate_gate() and not import_ready_from_validate:
        return False
    if block_on_validation_fail() and validation_level == "fail":
        return False
    if plan_status == "blocked":
        return False
    if data_gap_count > 0:
        return False
    return create_step_count > 0


def count_plan_steps(phases: Dict[str, Any]) -> tuple[int, int, int, List[Dict[str, Any]]]:
    """Return (create_count, data_gap_count, optional_gap_count, flat_steps)."""
    create_count = 0
    data_gap_count = 0
    optional_gap_count = 0
    flat: List[Dict[str, Any]] = []

    for phase_id, phase_data in (phases or {}).items():
        for step in phase_data.get("steps") or []:
            if not isinstance(step, dict):
                continue
            action = str(step.get("action") or "")
            row = {
                "phase_id": phase_id,
                "doctype": step.get("doctype"),
                "action": action,
                "records": int(step.get("records") or 0),
                "data_source": str(step.get("data_source") or ""),
                "criticality": step.get("criticality"),
            }
            flat.append(row)
            if action == "create" and row["records"] > 0:
                create_count += 1
            elif action == "data_gap":
                data_gap_count += 1
            elif action in ("optional_skip",):
                optional_gap_count += 1

    return create_count, data_gap_count, optional_gap_count, flat


def gate_summary(
    plan_status: PlanStatus,
    import_level: ImportLevel,
    *,
    create_step_count: int,
    data_gap_count: int,
    optional_gap_count: int,
    blocked_reasons: List[str],
) -> str:
    if import_level == "blocked" or plan_status == "blocked":
        reason = blocked_reasons[0] if blocked_reasons else "Import is blocked until validation and data gaps are resolved."
        return reason
    if import_level == "failed":
        return "No mapped records are ready to import. Upload missing files or fix validation errors."
    if import_level == "partial" or plan_status == "ready_with_gaps":
        parts = [f"{create_step_count} module(s) ready to import."]
        if optional_gap_count:
            parts.append(f"{optional_gap_count} optional module(s) deferred.")
        if data_gap_count:
            parts.append(f"{data_gap_count} critical gap(s) remain.")
        return " ".join(parts)
    return (
        f"Import plan is ready — {create_step_count} module(s) will be written to your live ERP "
        "in dependency order."
    )
