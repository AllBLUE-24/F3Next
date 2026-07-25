"""Schema resolver unit tests."""
from __future__ import annotations

from containers.implementation.readiness.schema import resolve_required_fields


def test_bridge_required_fields_for_item():
    fields, source = resolve_required_fields("Item")
    assert source == "bridge"
    assert "item_code" in fields


def test_live_mandatory_fields_preferred():
    live = [
        {"fieldname": "item_code", "mandatory": True},
        {"fieldname": "item_name", "mandatory": True},
        {"fieldname": "description", "mandatory": False},
    ]
    fields, source = resolve_required_fields("Item", live_fields=live)
    assert source == "live"
    assert fields == ["item_code", "item_name"]


def test_f3iche_defaults_subtracted():
    fields, _ = resolve_required_fields(
        "Item",
        f3iche_id="manufacturing_project_chemical",
    )
    assert "has_batch_no" not in fields
    assert "item_code" in fields
