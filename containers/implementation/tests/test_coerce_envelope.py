"""coerce_envelope — import phase dicts must not break NodeStatusEnvelope."""
from __future__ import annotations

from containers.implementation.is_workflow.quality_gate_hooks import coerce_envelope


def test_execute_import_phase_result_coerces_without_execution_logs_kwarg():
    env = coerce_envelope(
        {
            "phase": "phase_0_site_config",
            "status": "success",
            "steps_completed": 1,
            "steps_failed": 0,
            "records_created": 1,
            "execution_logs": [{"doctype": "UOM", "status": "success"}],
        }
    )
    assert env.status == "success"
    assert env.primary_result["phase"] == "phase_0_site_config"
    assert len(env.primary_result["execution_logs"]) == 1


def test_error_status_maps_to_failed():
    env = coerce_envelope({"status": "error", "steps_failed": 2})
    assert env.status == "failed"
    assert env.primary_result["steps_failed"] == 2
