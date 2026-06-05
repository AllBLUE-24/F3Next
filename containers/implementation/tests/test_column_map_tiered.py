"""Tests for tiered column mapping (KB fuzzy tier, no LLM)."""
from __future__ import annotations

from containers.implementation.mapping_agent.activities import _MappingEngine
from containers.implementation.mapping_agent.column_map_tiered import kb_fuzzy_map_columns
from containers.implementation.mapping_agent.kb import field_mappings as _kb_field_mappings


def test_kb_fuzzy_maps_vendor_name_to_supplier():
    kb = _kb_field_mappings()
    cols = ["PO_Number", "Vendor_Name", "Item", "Ordered_Qty"]
    engine = _MappingEngine()
    tier1 = engine.map_columns(cols, "Purchase Order")
    merged = kb_fuzzy_map_columns(cols, "Purchase Order", kb, already_mapped=tier1)
    assert merged.get("Vendor_Name") == "supplier"


def test_kb_fuzzy_maps_target_date_to_delivery_date():
    kb = _kb_field_mappings()
    cols = ["Client", "Project", "Target_Date", "Product"]
    engine = _MappingEngine()
    tier1 = engine.map_columns(cols, "Sales Order")
    merged = kb_fuzzy_map_columns(cols, "Sales Order", kb, already_mapped=tier1)
    assert merged.get("Target_Date") == "delivery_date"
