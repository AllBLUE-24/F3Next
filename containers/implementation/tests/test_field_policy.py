"""Tests for default-aware field policy."""
from __future__ import annotations

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
