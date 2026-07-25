"""Readiness gate tests."""
from __future__ import annotations

from containers.implementation.readiness.readiness_gate import compute_readiness_level
from containers.implementation.readiness.models import ReadinessMatrix


def test_red_when_blocking_gap_items():
    level = compute_readiness_level(
        matrix=ReadinessMatrix(),
        doctype_gaps=[],
        field_gaps=[],
        pre_analysis={},
        gap_items=[{"severity": "blocking", "metadata": {"tier": "critical"}}],
    )
    assert level == "red"


def test_green_when_no_gaps():
    level = compute_readiness_level(
        matrix=ReadinessMatrix(),
        doctype_gaps=[],
        field_gaps=[],
        pre_analysis={"ready_doctypes": [{"doctype": "Item"}], "scope_doctypes": ["Item"]},
        gap_items=[],
    )
    assert level == "green"
