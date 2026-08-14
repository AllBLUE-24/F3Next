"""F3iche import_field_policy loader."""
from __future__ import annotations

from containers.implementation.is_common.f3iche_policy import (
    always_ask_fields,
    deferred_fields,
    defer_until_post_mvp,
    f3iche_default_for,
    is_deferred_doctype,
    must_ask_for_doctype,
)
from containers.implementation.data_readiness_agent.field_policy import classify_missing_fields


def test_manufacturing_project_chemical_policy():
    fid = "manufacturing_project_chemical"
    assert f3iche_default_for("Item", "item_group", fid) == "Consumable"
    assert "item_group" in always_ask_fields(fid)
    assert "income_account" in deferred_fields(fid)
    assert defer_until_post_mvp(fid) == set()
    assert not must_ask_for_doctype("BOM", fid)
    assert not is_deferred_doctype("Stock Entry", fid)


def test_f3iche_does_not_defer_required_doctype_fields():
    kb = {"doctypes": {}}
    assumed, _, blocking = classify_missing_fields(
        "Stock Entry",
        ["stock_entry_type", "items"],
        [],
        kb,
        f3iche_id="manufacturing_project_chemical",
    )
    assert blocking == ["stock_entry_type", "items"]
    assert assumed == []


def test_f3iche_field_policy_overrides_generic_default():
    assumed, _, blocking = classify_missing_fields(
        "Item",
        ["item_group", "income_account"],
        [],
        {"doctypes": {}},
        f3iche_id="manufacturing_project_chemical",
    )
    assert assumed == []
    assert blocking == ["item_group"]
