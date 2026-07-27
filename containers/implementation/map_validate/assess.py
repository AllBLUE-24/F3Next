"""Orchestrate offline Step 4 assess."""
from __future__ import annotations

from typing import Any, Dict

from containers.implementation.map_validate.config import require_readiness_gate
from containers.implementation.map_validate.gate import (
    compute_import_ready,
    compute_validation_level,
    gate_summary,
)
from containers.implementation.map_validate.inputs import MapValidateInputs
from containers.implementation.map_validate.map_offline import run_offline_mapping
from containers.implementation.map_validate.models import MapValidateReport
from containers.implementation.validation_agent.activities import _ValidationEngine


def assess_map_validate_offline(inputs: MapValidateInputs) -> MapValidateReport:
    """Deterministic map + validate for harness and offline golden gate."""
    if require_readiness_gate() and (inputs.readiness_level or "").lower() == "red":
        return MapValidateReport(
            validation_level="fail",
            import_ready=False,
            executive_summary="Readiness gate is RED — upload missing data before mapping.",
        )

    map_results, mapped_data = run_offline_mapping(inputs)
    engine = _ValidationEngine()
    validation_report = engine.validate(mapped_data, inputs.target_structure)
    level = compute_validation_level(validation_report)
    errors = list(validation_report.get("errors") or [])
    warnings = list(validation_report.get("warnings") or [])
    for check in validation_report.get("checks") or []:
        if isinstance(check, dict):
            errors.extend(check.get("errors") or [])
            warnings.extend(check.get("warnings") or [])

    seeds = list(inputs.target_structure.get("seed_doctypes") or [])
    mapped_set = set(mapped_data.keys())
    blocking_seeds = [s for s in seeds if s not in mapped_set and s not in set(inputs.target_structure.get("deferred_doctypes") or [])]

    import_ready = compute_import_ready(
        level,
        map_results=map_results,
        blocking_unmapped_seeds=blocking_seeds[:3] if len(blocking_seeds) > len(seeds) // 2 else [],
    )
    requires_ack = level == "partial"

    return MapValidateReport(
        map_results=map_results,
        mapped_doctypes=sorted(mapped_data.keys()),
        validation_report=validation_report,
        validation_level=level,
        import_ready=import_ready,
        requires_acknowledgment=requires_ack,
        executive_summary=gate_summary(
            level,
            error_count=len(errors),
            warning_count=len(warnings),
            mapped_doctypes=sorted(mapped_data.keys()),
        ),
        error_count=len(errors),
        warning_count=len(warnings),
    )
