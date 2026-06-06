"""F3iche import_field_policy loader."""
from __future__ import annotations

from containers.implementation.is_common.f3iche_policy import (
    default_when_missing,
    defer_until_post_mvp,
    f3iche_default_for,
    is_deferred_doctype,
    must_ask_for_doctype,
)
from containers.implementation.data_readiness_agent.field_policy import classify_missing_fields


def test_manufacturing_project_chemical_policy():
    fid = "manufacturing_project_chemical"
    assert f3iche_default_for("Item", "item_group", fid) == "Consumable"
    assert "Stock Entry" in defer_until_post_mvp(fid)
    assert must_ask_for_doctype("BOM", fid)
    assert is_deferred_doctype("Stock Entry", fid)


def test_f3iche_defers_doctype_blocking():
    kb = {"doctypes": {}}
    assumed, _, blocking = classify_missing_fields(
        "Stock Entry",
        ["stock_entry_type", "items"],
        [],
        kb,
        f3iche_id="manufacturing_project_chemical",
    )
    assert blocking == []
    assert assumed == []
