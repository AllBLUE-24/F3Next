"""Offline import plan build + finalize (no DB/R2)."""
from __future__ import annotations

from typing import Any, Dict, List, Set, Tuple

from containers.implementation.import_agent.activities import _ImportEngine, _load_baseline_data
from containers.implementation.import_agent.mvp_import_scope import (
    blocks_import_when_unmapped,
    is_out_of_mvp_scope,
    parse_mvp_scope_from_target,
)
from containers.implementation.is_common.doctype_resolver import resolve_doctype
from containers.implementation.mapping_agent.corpus_merge import inject_missing_mapped_steps

_ERPNEXT_AUTO_CONFIG = frozenset({
    "Company",
    "Chart of Accounts",
    "Account",
    "Cost Center",
    "Fiscal Year",
    "Currency",
    "Warehouse",
    "Tax Template",
})


def build_import_plan_offline(
    setup_steps: List[Dict[str, Any]],
    mapped_data_dict: Dict[str, Dict[str, Any]],
    validation_status: str,
) -> Dict[str, Any]:
    """Build initial import plan from graph setup_steps + mapped corpus."""
    engine = _ImportEngine()
    return engine.build_plan(
        setup_steps,
        mapped_data_dict,
        validation_status,
    )


def finalize_import_plan_offline(
    plan: Dict[str, Any],
    mapped_dict: Dict[str, Dict[str, Any]],
    target_structure: Dict[str, Any],
    *,
    has_validation_failures: bool = False,
    criticality_map: Dict[str, str] | None = None,
) -> Tuple[str, Dict[str, Any], List[str]]:
    """
    Resolve plan steps against mapped paths and MVP scope.

    Returns (plan_status, updated_phases, optional_gaps).
    """
    if plan.get("status") == "blocked":
        return "blocked", plan.get("phases") or {}, []

    baseline_data = _load_baseline_data()
    mvp_seeds, deferred = parse_mvp_scope_from_target(target_structure)
    crit_map = dict(criticality_map or {})

    phases = inject_missing_mapped_steps(dict(plan.get("phases") or {}), mapped_dict)

    plan_status = "ready"
    has_critical_gap = False
    has_noncritical_gap = False
    optional_gaps: List[str] = []
    updated_phases: Dict[str, Any] = {}

    if has_validation_failures:
        plan_status = "blocked"

    for phase_id, phase_data in phases.items():
        steps = phase_data.get("steps", [])
        updated_steps = []
        for step in steps:
            dt = step.get("doctype")
            action = step.get("action")
            unmapped = dt not in mapped_dict
            needs_file = action in ("create", "data_gap", "optional_skip") or step.get("data_source") == "pending_mapping"

            if needs_file and unmapped:
                dt_resolved = resolve_doctype(dt or "")
                baseline_vals = baseline_data.get(dt_resolved) or baseline_data.get(dt or "")

                if baseline_vals:
                    step["action"] = "seed_from_baseline"
                    step["data_source"] = "baseline"
                    step["records"] = len(baseline_vals)
                    updated_steps.append(step)
                    continue

                if dt_resolved in _ERPNEXT_AUTO_CONFIG or (dt or "") in _ERPNEXT_AUTO_CONFIG:
                    step["action"] = "skip"
                    step["data_source"] = "auto"
                    step["records"] = 0
                    updated_steps.append(step)
                    continue

                if action == "optional_skip" or is_out_of_mvp_scope(dt_resolved, mvp_seeds, deferred):
                    has_noncritical_gap = True
                    optional_gaps.append(dt or "")
                    step["action"] = "optional_skip"
                    step["data_source"] = "none"
                    step["records"] = 0
                    updated_steps.append(step)
                    continue

                if not blocks_import_when_unmapped(
                    dt or "", mvp_seeds, deferred, crit_map, phase_id,
                ):
                    step["action"] = "optional_skip"
                    step["data_source"] = "none"
                    step["records"] = 0
                    has_noncritical_gap = True
                    optional_gaps.append(dt or "")
                else:
                    step["action"] = "data_gap"
                    step["data_source"] = "none"
                    step["records"] = 0
                    step["criticality"] = "critical"
                    has_critical_gap = True
            elif needs_file and dt in mapped_dict:
                step["data_source"] = mapped_dict[dt].get("r2_path", step.get("data_source"))
                step["records"] = mapped_dict[dt].get("total_rows", 0)
                if mapped_dict[dt].get("validation_status") == "failed":
                    plan_status = "blocked"
                    has_critical_gap = True

            updated_steps.append(step)

        updated_phases[phase_id] = {
            "name": phase_data.get("name"),
            "steps": updated_steps,
        }

    if has_validation_failures or has_critical_gap:
        plan_status = "blocked"
    elif has_noncritical_gap:
        plan_status = "ready_with_gaps"
    else:
        plan_status = "ready"

    return plan_status, updated_phases, optional_gaps


def mapped_dict_from_offline_records(
    mapped_data: Dict[str, Any],
    *,
    project_id: str,
    validation_level: str = "partial",
) -> Dict[str, Dict[str, Any]]:
    """Convert Step 4 offline mapped_data {doctype: {records}} to finalize shape."""
    out: Dict[str, Dict[str, Any]] = {}
    val_status = "failed" if validation_level == "fail" else "passed"
    for dt, payload in (mapped_data or {}).items():
        records = payload.get("records") if isinstance(payload, dict) else payload
        if not records:
            continue
        out[dt] = {
            "r2_path": f"harness/{project_id}/mappings/mapped_payloads/{dt}.json",
            "total_rows": len(records) if isinstance(records, list) else int(payload.get("total_rows") or 0),
            "validation_status": val_status,
        }
    return out


def criticality_map_from_target(target_structure: Dict[str, Any]) -> Dict[str, str]:
    """Build a minimal criticality map from target seed phases when no DB readiness row."""
    out: Dict[str, str] = {}
    for step in target_structure.get("setup_steps") or []:
        if not isinstance(step, dict):
            continue
        dt = str(step.get("doctype") or "").strip()
        if not dt:
            continue
        phase = str(step.get("phase") or "")
        if phase.startswith("phase_a") or phase.startswith("phase_b"):
            out[dt] = "critical"
        elif phase.startswith("phase_c"):
            out[dt] = "non_critical"
        else:
            out[dt] = "optional"
    return out
