"""Tests for default-aware field policy and readiness helpers."""
from __future__ import annotations

from containers.implementation.data_readiness_agent.activities import (
    _criticality_from_phase,
    _recompute_viability_summary,
    _tag_bottleneck_gaps,
)
from containers.implementation.data_readiness_agent.field_policy import (
    assess_field_coverage,
    classify_missing_fields,
)
from containers.implementation.mapping_agent.kb import field_mappings as _kb_field_mappings


def test_sales_order_target_date_covers_delivery_date():
    kb = _kb_field_mappings()
    policy = assess_field_coverage(
        "Sales Order",
        ["customer", "transaction_date"],
        ["Client", "Project", "Target_Date", "Product"],
        kb,
    )
    assert "delivery_date" not in policy["blocking_fields"]
    assert policy["can_proceed_without"] is True


def test_sales_order_blocks_without_date_columns():
    kb = _kb_field_mappings()
    policy = assess_field_coverage(
        "Sales Order",
        ["customer"],
        ["Client", "Product"],
        kb,
    )
    assert "delivery_date" in policy["blocking_fields"] or "transaction_date" in policy["blocking_fields"]


def test_phase_d_projects_is_non_critical():
    assert _criticality_from_phase("phase_d_projects") == "non_critical"


def test_bottleneck_tags_stock_entry_deferrable_when_not_mvp_seed():
    pre = {
        "missing_doctypes": [{"doctype": "Stock Entry", "phase": "phase_c_transactional"}],
        "partial_doctypes": [],
        "summary": {"n_blocking_missing": 1},
    }
    _tag_bottleneck_gaps(
        pre,
        {"primary_bottleneck": "Lack of real-time tracking for material consumption against projects."},
        {"seed_doctypes": ["Customer", "Sales Order"]},
    )
    summary = _recompute_viability_summary(pre)
    assert pre["missing_doctypes"][0].get("can_proceed_without") is True
    assert summary["minimum_viable_possible"] is True


def test_bottleneck_does_not_soften_mvp_seed_stock_entry():
    pre = {
        "missing_doctypes": [{"doctype": "Stock Entry", "phase": "phase_c_transactional"}],
        "partial_doctypes": [],
        "summary": {"n_blocking_missing": 1},
    }
    _tag_bottleneck_gaps(
        pre,
        {"primary_bottleneck": "Lack of real-time tracking for material consumption against projects."},
        {"seed_doctypes": ["Customer", "Sales Order", "Stock Entry"]},
    )
    summary = _recompute_viability_summary(pre)
    assert pre["missing_doctypes"][0].get("can_proceed_without") is not True
    assert summary["minimum_viable_possible"] is False


def test_preflight_blocking_fields_classification():
    kb = _kb_field_mappings()
    _, _, blocking = classify_missing_fields(
        "Purchase Order",
        ["supplier", "items"],
        [],
        kb,
        columns=["PO_Number", "Item"],
    )
    assert "supplier" in blocking
