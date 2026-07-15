"""Tests for discovery archetype registry (Phase 0)."""

from __future__ import annotations

from containers.discovery.archetype_registry import (
    best_signal_match,
    get_by_id,
    list_archetype_ids,
    merged_archetypes,
    resolve_seed_doctypes,
)

CHEMICAL_F3ICHE = "manufacturing_project_chemical"

CHEMICAL_TEMPLATE = [
    "Item",
    "Batch",
    "BOM",
    "Work Order",
    "Job Card",
    "Project",
    "Stock Entry",
    "Quality Inspection",
    "Quotation",
    "Sales Order",
]


def test_merged_archetypes_includes_f3iche_and_catalog():
    ids = list_archetype_ids(CHEMICAL_F3ICHE)
    assert "factory_wip_bridge" in ids
    assert "basic_inventory" in ids
    assert "subcontracting_raw_material_leakage" in ids
    assert "custom_order_pipeline" in ids


def test_f3iche_overrides_catalog_same_id():
    merged = {a["archetype_id"]: a for a in merged_archetypes(CHEMICAL_F3ICHE)}
    f3iche_wip = get_by_id("factory_wip_bridge", CHEMICAL_F3ICHE)
    assert f3iche_wip is not None
    assert "Quality Inspection" in (f3iche_wip.get("day1_seed_hints") or [])


def test_get_by_id_unknown_returns_none():
    assert get_by_id("not_a_real_archetype", CHEMICAL_F3ICHE) is None


def test_signal_match_part_a_b_inventory():
    text = "stranded hardener Part A and Part B mismatch hazmat 55 gallon drum"
    match = best_signal_match(text, CHEMICAL_F3ICHE)
    assert match is not None
    archetype, score = match
    assert archetype["archetype_id"] == "inventory_visibility"
    assert score >= 2


def test_signal_match_wip_excel():
    text = "excel sheets flying around work in progress black box true production cost"
    match = best_signal_match(text, CHEMICAL_F3ICHE)
    assert match is not None
    archetype, score = match
    assert archetype["archetype_id"] == "excel_bom_disconnect"
    assert score >= 1


def test_resolve_seeds_intersection_with_template():
    archetype = get_by_id("inventory_visibility", CHEMICAL_F3ICHE)
    assert archetype is not None
    seeds, extensions = resolve_seed_doctypes(archetype, CHEMICAL_TEMPLATE)
    assert "Item" in seeds
    assert "Batch" in seeds
    assert "Stock Entry" in seeds
    # Warehouse not in chemical template but in graph — may appear as extension
    if "Warehouse" in seeds:
        assert "Warehouse" in extensions


def test_resolve_seeds_applies_defer_typically():
    archetype = get_by_id("scrap_wastage", CHEMICAL_F3ICHE)
    assert archetype is not None
    seeds, _ = resolve_seed_doctypes(archetype, CHEMICAL_TEMPLATE + ["Purchase Order", "Supplier"])
    assert "Purchase Order" not in seeds
    assert "Supplier" not in seeds
    assert "Stock Entry" in seeds
