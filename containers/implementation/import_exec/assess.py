"""Orchestrate offline Step 5 assess."""
from __future__ import annotations

from typing import Any, Dict, List

from containers.implementation.import_exec.gate import (
    compute_import_level,
    compute_import_ready,
    count_plan_steps,
    gate_summary,
)
from containers.implementation.import_exec.inputs import ImportInputs, build_import_inputs
from containers.implementation.import_exec.models import ImportExecutionReport, ImportStepRow
from containers.implementation.import_exec.plan_offline import (
    build_import_plan_offline,
    finalize_import_plan_offline,
)
from containers.implementation.import_agent.phase_order import sort_phases


def assess_import_offline(inputs: ImportInputs) -> ImportExecutionReport:
    """Deterministic import plan assess for harness and offline golden gate."""
    blocked_reasons: List[str] = []

    if inputs.validation_level == "fail":
        blocked_reasons.append("Validation failed — fix errors before import.")

    validation_status = "fail" if inputs.validation_level == "fail" else "partial"
    raw_plan = build_import_plan_offline(
        inputs.setup_steps,
        inputs.mapped_data_dict,
        validation_status,
    )

    if raw_plan.get("status") == "blocked":
        return ImportExecutionReport(
            plan_status="blocked",
            import_level="blocked",
            import_ready=False,
            executive_summary=gate_summary(
                "blocked",
                "blocked",
                create_step_count=0,
                data_gap_count=0,
                optional_gap_count=0,
                blocked_reasons=[str(raw_plan.get("reason") or "Validation blocked import plan.")],
            ),
            blocked_reasons=[str(raw_plan.get("reason") or "Validation blocked import plan.")],
        )

    has_validation_failures = inputs.validation_level == "fail" or bool(inputs.validation_failed_doctypes)
    plan_status, phases, optional_gaps = finalize_import_plan_offline(
        raw_plan,
        inputs.mapped_data_dict,
        inputs.target_structure,
        has_validation_failures=has_validation_failures,
        criticality_map=inputs.criticality_map,
    )

    create_count, data_gap_count, optional_gap_count, flat = count_plan_steps(phases)
    ordered = [pid for pid, _ in sort_phases(phases)]

    if not inputs.import_ready_from_validate:
        blocked_reasons.append("Validate step has not approved import yet.")
    if data_gap_count:
        blocked_reasons.append(f"{data_gap_count} critical data gap(s) in import plan.")
    if inputs.validation_failed_doctypes:
        blocked_reasons.append(
            f"Validation failed for: {', '.join(inputs.validation_failed_doctypes[:5])}."
        )

    import_ready = compute_import_ready(
        plan_status,
        validation_level=inputs.validation_level,
        import_ready_from_validate=inputs.import_ready_from_validate,
        create_step_count=create_count,
        data_gap_count=data_gap_count,
    )
    import_level = compute_import_level(
        plan_status,
        create_step_count=create_count,
        data_gap_count=data_gap_count,
    )

    steps = [
        ImportStepRow(
            phase_id=row["phase_id"],
            doctype=str(row.get("doctype") or ""),
            action=str(row.get("action") or ""),
            records=int(row.get("records") or 0),
            data_source=str(row.get("data_source") or ""),
            criticality=row.get("criticality"),
        )
        for row in flat
    ]

    return ImportExecutionReport(
        plan_status=plan_status,
        import_level=import_level,
        import_ready=import_ready,
        phases=phases,
        steps=steps,
        create_step_count=create_count,
        data_gap_count=data_gap_count,
        optional_gap_count=optional_gap_count,
        ordered_phase_ids=ordered,
        executive_summary=gate_summary(
            plan_status,
            import_level,
            create_step_count=create_count,
            data_gap_count=data_gap_count,
            optional_gap_count=optional_gap_count,
            blocked_reasons=blocked_reasons,
        ),
        blocked_reasons=blocked_reasons,
    )


def assess_import_from_map_validate(
    *,
    project_id: str,
    setup_steps: List[Dict[str, Any]],
    target_structure: Dict[str, Any],
    mapped_data: Dict[str, Any],
    map_validate_report: Any,
) -> ImportExecutionReport:
    """Bridge Step 4 offline output into Step 5 assess."""
    from containers.implementation.import_exec.plan_offline import (
        criticality_map_from_target,
        mapped_dict_from_offline_records,
    )

    validation_level = getattr(map_validate_report, "validation_level", None) or "partial"
    import_ready_from_validate = bool(getattr(map_validate_report, "import_ready", False))

    mapped_dict = mapped_dict_from_offline_records(
        mapped_data,
        project_id=project_id,
        validation_level=str(validation_level),
    )

    return assess_import_offline(
        build_import_inputs(
            project_id=project_id,
            setup_steps=setup_steps,
            target_structure=target_structure,
            mapped_data_dict=mapped_dict,
            validation_level=str(validation_level),
            import_ready_from_validate=import_ready_from_validate,
            criticality_map=criticality_map_from_target(target_structure),
        )
    )
