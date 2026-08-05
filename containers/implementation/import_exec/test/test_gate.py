"""Gate tests for Step 5 import."""
from __future__ import annotations

from containers.implementation.import_exec.gate import (
    compute_import_level,
    compute_import_ready,
    count_plan_steps,
)


def test_import_ready_blocked_on_data_gaps():
    ready = compute_import_ready(
        "ready",
        validation_level="partial",
        import_ready_from_validate=True,
        create_step_count=2,
        data_gap_count=1,
    )
    assert ready is False


def test_import_ready_when_plan_ready_with_creates():
    ready = compute_import_ready(
        "ready",
        validation_level="partial",
        import_ready_from_validate=True,
        create_step_count=3,
        data_gap_count=0,
    )
    assert ready is True


def test_import_level_partial_for_ready_with_gaps():
    level = compute_import_level(
        "ready_with_gaps",
        create_step_count=2,
        data_gap_count=0,
    )
    assert level == "partial"


def test_count_plan_steps():
    phases = {
        "phase_b_master": {
            "steps": [
                {"doctype": "Customer", "action": "create", "records": 2, "data_source": "x"},
                {"doctype": "Item", "action": "data_gap", "records": 0, "data_source": "none"},
            ],
        },
    }
    create_count, data_gap_count, optional_count, flat = count_plan_steps(phases)
    assert create_count == 1
    assert data_gap_count == 1
    assert optional_count == 0
    assert len(flat) == 2
