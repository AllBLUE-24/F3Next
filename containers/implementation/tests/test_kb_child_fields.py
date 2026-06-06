"""KB audit: transactional doctypes with mandatory items tables need child_fields."""
from __future__ import annotations

import pytest

from containers.knowledge_base.erpnext.schema.compose import compose_field_mappings

# Phase 0 scope: PO/SO must have child_fields before dry-run readiness gates pass.
_TRANSACTIONAL_WITH_ITEMS = (
    "Sales Order",
    "Purchase Order",
)


@pytest.mark.parametrize("doctype", _TRANSACTIONAL_WITH_ITEMS)
def test_mandatory_items_table_has_child_fields(doctype: str):
    kb = compose_field_mappings()
    dt_cfg = (kb.get("doctypes") or {}).get(doctype) or {}
    fmap = dt_cfg.get("field_mappings") or {}
    items_cfg = fmap.get("items") or {}
    assert str(items_cfg.get("fieldtype") or "").lower() == "table"
    assert items_cfg.get("mandatory") is True
    child_fields = items_cfg.get("child_fields") or {}
    assert child_fields, f"{doctype}.items missing child_fields in KB"
    fieldnames = {
        str(c.get("fieldname"))
        for c in child_fields.values()
        if isinstance(c, dict) and c.get("fieldname")
    }
    assert "item_code" in fieldnames, f"{doctype} items child_fields missing item_code"
    assert "qty" in fieldnames, f"{doctype} items child_fields missing qty"
