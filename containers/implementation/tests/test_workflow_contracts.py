"""Unit tests for fail-closed workflow progression predicates."""

from containers.implementation.is_workflow.contracts import (
    import_phase_failed,
    mapping_blocks_progress,
    readiness_blocks_progress,
)


def test_readiness_requires_explicit_viability():
    assert readiness_blocks_progress("success", {}) is True
    assert readiness_blocks_progress(
        "success",
        {"minimum_viable_import_possible": True},
    ) is False
    assert readiness_blocks_progress(
        "failed",
        {"minimum_viable_import_possible": True},
    ) is True


def test_mapping_requires_at_least_one_usable_file():
    assert mapping_blocks_progress(0, 3) is True
    assert mapping_blocks_progress(1, 3) is False
    assert mapping_blocks_progress(0, 0) is True


def test_import_phase_failure_aborts_on_status_or_step_failure():
    assert import_phase_failed({"status": "error", "steps_failed": 0}) is True
    assert import_phase_failed({"status": "complete", "steps_failed": 1}) is True
    assert import_phase_failed({"status": "complete", "steps_failed": 0}) is False
    assert import_phase_failed("complete") is True
