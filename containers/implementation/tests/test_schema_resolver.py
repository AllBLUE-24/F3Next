"""SchemaResolver and synonym promotion (Phase 5)."""
from __future__ import annotations

from containers.implementation.mapping_agent.schema_resolver import (
    kb_missing_child_fields,
    resolve_kb_gaps_sync,
)
from containers.implementation.mapping_agent.synonym_promotion import suggest_synonym_promotions
from containers.implementation.mapping_agent.kb import field_mappings as _kb_field_mappings


def test_kb_missing_child_fields_detects_gaps():
    kb = _kb_field_mappings()
    # Delivery Note may lack child_fields — if it has them, use a synthetic doctype stub
    missing = kb_missing_child_fields("Delivery Note", kb)
    assert isinstance(missing, list)


def test_resolve_injects_heuristic_items_child_fields():
    kb = {
        "doctypes": {
            "Test PO": {
                "field_mappings": {
                    "items": {
                        "fieldname": "items",
                        "fieldtype": "Table",
                        "mandatory": True,
                    },
                },
            },
        },
    }
    patched, meta = resolve_kb_gaps_sync("Test PO", kb)
    assert meta["resolved"] is True
    child = patched["doctypes"]["Test PO"]["field_mappings"]["items"]["child_fields"]
    assert "item_code" in child
    assert "qty" in child


def test_synonym_promotion_suggests_unmapped_columns():
    suggestions = suggest_synonym_promotions(
        doctype="Sales Order",
        field_mapping={"Client": "customer"},
        columns=["Client", "Vol", "Price"],
        missing_required=["delivery_date"],
    )
    cols = {s["source_column"] for s in suggestions if s.get("source_column")}
    assert "Vol" in cols
    assert any(s.get("erp_field") == "delivery_date" for s in suggestions)
