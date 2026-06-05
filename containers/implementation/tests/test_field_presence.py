"""Tests for shared mapped-row required-field presence (preflight + validate)."""
from __future__ import annotations

from containers.implementation.is_common.field_presence import (
    field_present_in_mapped_row,
    missing_required_on_records,
)
from containers.implementation.mapping_agent.defaults import fold_child_tables
from containers.implementation.mapping_agent.preflight_fields import preflight_mapped_records


def test_empty_items_array_not_present():
    row = {"customer": "Acme", "transaction_date": "2026-01-01", "items": []}
    assert field_present_in_mapped_row("items", row) is False


def test_populated_items_child_present():
    row = {
        "customer": "Acme",
        "items": [{"item_code": "FG-1", "qty": 10}],
    }
    assert field_present_in_mapped_row("items", row) is True


def test_namespaced_items_keys_present():
    row = {"supplier": "Vendor A", "items.item_code": "RM-X", "items.qty": 5}
    assert field_present_in_mapped_row("items", row) is True


def test_fold_child_tables_then_preflight_passes_po():
    from containers.implementation.mapping_agent.defaults import apply_defaults_and_normalize

    raw = [{
        "supplier": "Gupta Chemical Traders",
        "items.item_code": "RM-EPOX-LIQ",
        "items.qty": 2000,
        "items.rate": 4.60,
    }]
    folded = apply_defaults_and_normalize("Purchase Order", fold_child_tables("Purchase Order", raw))
    preflight = preflight_mapped_records("Purchase Order", folded)
    assert "items" not in preflight["missing_fields"]


def test_preflight_blocks_po_without_items():
    rows = [{"supplier": "Gupta Chemical Traders", "transaction_date": "2026-01-01", "items": []}]
    preflight = preflight_mapped_records("Purchase Order", rows)
    assert preflight["blocking"] is True
    assert "items" in preflight["missing_fields"]


def test_missing_required_on_records():
    rows = [{"customer": "Rohan Construction", "items": []}]
    missing = missing_required_on_records("Sales Order", rows, ["customer", "items", "delivery_date"])
    assert "items" in missing
    assert "delivery_date" in missing
    assert "customer" not in missing
