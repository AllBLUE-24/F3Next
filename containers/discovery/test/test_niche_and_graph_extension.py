"""Tests for Phase 3 niche resolver and graph extension allowlist."""

from __future__ import annotations

from containers.discovery.archetype_registry import resolve_seed_doctypes
from containers.discovery.niche_resolver import resolve_discovery_f3iche_niche

CHEMICAL_TEMPLATE = ["Item", "BOM", "Work Order", "Delivery Note", "Customer"]


def test_toll_manufacturer_not_chemical_niche():
    text = (
        "We design chemical formulations but use a toll manufacturer in Gujarat. "
        "Subcontractor wastes raw materials."
    )
    niche = resolve_discovery_f3iche_niche(
        discovery_f3iche="manufacturing",
        industry="chemical formulations",
        chat_transcript=text,
    )
    assert niche == "manufacturing_fabrication_jobshop"


def test_wip_epoxy_still_chemical_niche():
    text = (
        "Industrial epoxy floor coatings. Zero visibility into WIP. "
        "Excel sheets on the shop floor."
    )
    niche = resolve_discovery_f3iche_niche(
        discovery_f3iche="manufacturing",
        industry="manufacturing",
        chat_transcript=text,
    )
    assert niche == "manufacturing_project_chemical"


def test_prefabricated_panel_procurement_niche():
    text = (
        "We assemble pre-fabricated panels. Our bottleneck is strictly purchasing "
        "and supplier lead times on material requests."
    )
    niche = resolve_discovery_f3iche_niche(
        discovery_f3iche="manufacturing",
        industry="",
        chat_transcript=text,
    )
    assert niche == "manufacturing_fabrication_jobshop"


def test_warranty_archetype_graph_extends_service_doctypes():
    archetype = {
        "archetype_id": "untracked_warranty_leakage",
        "day1_seed_hints": ["Warranty Claim", "Serial No", "Delivery Note", "Customer"],
    }
    seeds, extensions = resolve_seed_doctypes(archetype, CHEMICAL_TEMPLATE)
    assert "Warranty Claim" in seeds
    assert "Warranty Claim" in extensions
    assert "Customer" in seeds
