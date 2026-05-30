"""Tests for unified submit-after-create gate (IS + OS)."""

from shared.erp_policies.submit_gate import (
    COMMIT_CONFIDENCE_AUTO_SUBMIT_THRESHOLD,
    is_dependency_submit_required,
    phase_child_doctypes,
    should_submit_after_create,
)


def test_phase_child_doctypes_from_steps():
    steps = [
        {"doctype": "BOM", "action": "create"},
        {"doctype": "Work Order", "action": "create"},
        {"doctype": "Item", "action": "seed"},
    ]
    assert phase_child_doctypes(steps) == {"BOM", "Work Order"}


def test_bom_submits_when_work_order_in_same_phase():
    children = {"Work Order", "Stock Entry"}
    assert is_dependency_submit_required("BOM", children) is True
    assert should_submit_after_create(
        "BOM",
        context="import",
        commit_confidence=0.5,
        phase_child_doctypes=children,
        execution_confirmed=False,
    ) is True


def test_bom_submits_when_work_order_planned_in_later_phase():
    phases = {
        "phase_b_master": {
            "steps": [{"doctype": "BOM", "action": "create"}],
        },
        "phase_c_transactional": {
            "steps": [{"doctype": "Work Order", "action": "create"}],
        },
    }
    from shared.erp_policies.submit_gate import all_plan_create_doctypes

    planned = all_plan_create_doctypes(phases)
    assert "Work Order" in planned
    assert should_submit_after_create(
        "BOM",
        context="import",
        commit_confidence=0.5,
        phase_child_doctypes=planned,
        execution_confirmed=False,
    ) is True


def test_bom_not_submitted_without_dependent_child_and_low_confidence():
    assert should_submit_after_create(
        "BOM",
        context="import",
        commit_confidence=0.5,
        phase_child_doctypes={"Stock Entry"},
        execution_confirmed=False,
    ) is False


def test_medium_risk_submits_at_high_confidence():
    assert should_submit_after_create(
        "BOM",
        context="import",
        commit_confidence=COMMIT_CONFIDENCE_AUTO_SUBMIT_THRESHOLD,
        phase_child_doctypes=set(),
        execution_confirmed=False,
    ) is True


def test_high_risk_requires_execution_confirmed_on_import():
    assert should_submit_after_create(
        "Sales Invoice",
        context="import",
        commit_confidence=0.95,
        phase_child_doctypes=set(),
        execution_confirmed=False,
    ) is False
    assert should_submit_after_create(
        "Sales Invoice",
        context="import",
        commit_confidence=0.95,
        phase_child_doctypes=set(),
        execution_confirmed=True,
    ) is True


def test_item_master_never_submits():
    assert should_submit_after_create(
        "Item",
        context="import",
        commit_confidence=1.0,
        phase_child_doctypes={"Work Order"},
        execution_confirmed=True,
    ) is False
