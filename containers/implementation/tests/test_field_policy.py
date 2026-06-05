"""Tests for default-aware field policy and readiness helpers."""
from __future__ import annotations

from containers.implementation.data_readiness_agent.activities import (
    _criticality_from_phase,
    _tag_bottleneck_gaps,
)
from containers.implementation.data_readiness_agent.field_policy import (
    classify_missing_fields,
    identity_satisfied,
    resolve_default,
)
from containers.implementation.mapping_agent.kb import field_mappings as _kb_field_mappings


def test_customer_defaults_for_group_and_territory():
    kb = _kb_field_mappings()
    assumed, defaultable, must_ask = classify_missing_fields(
        "Customer",
        ["customer_group", "territory", "customer_type"],
        ["customer_name"],
        kb,
    )
    assert not must_ask
    assert len(assumed) == 3
    assert resolve_default("Customer", "territory", kb) == "All Territories"


def test_identity_from_company_name_column():
    assert identity_satisfied(
        "Customer",
        matched_fields=[],
        columns=["Company_Name", "Role", "City"],
    )


def test_party_row_count_satisfies_identity():
    assert identity_satisfied(
        "Supplier",
        matched_fields=[],
        columns=["Company_Name", "Role"],
        party_row_count=2,
    )


def test_phase_d_projects_is_non_critical():
    assert _criticality_from_phase("phase_d_projects") == "non_critical"


def test_bottleneck_tags_stock_entry_gap():
    pre = {
        "missing_doctypes": [{"doctype": "Stock Entry", "phase": "phase_c_transactional"}],
        "partial_doctypes": [],
    }
    _tag_bottleneck_gaps(
        pre,
        {"primary_bottleneck": "Lack of real-time tracking for material consumption against projects."},
    )
    entry = pre["missing_doctypes"][0]
    assert entry.get("bottleneck_relevant") is True
    assert entry.get("can_proceed_without") is True
