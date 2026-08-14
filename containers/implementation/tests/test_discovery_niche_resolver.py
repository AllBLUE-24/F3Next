"""Tests for discovery → specific niche resolution."""
from __future__ import annotations

from containers.implementation.signals_agent.discovery_niche_resolver import (
    discovery_evidence_bullets,
    resolve_niche_from_discovery,
    resolve_niche_from_text,
)

NICHE_IDS = [
    "trading_fmcg_distributor",
    "manufacturing_garment_variants",
    "manufacturing_project_chemical",
    "manufacturing_fabrication_jobshop",
    "service_professional",
]


def test_broad_manufacturing_with_chemical_industry():
    niche = resolve_niche_from_discovery(
        discovery_f3iche="manufacturing",
        discovery_industry="Epoxy floor coatings manufacturer",
        niche_ids=NICHE_IDS,
    )
    assert niche == "manufacturing_project_chemical"


def test_chat_hints_project_installation():
    niche = resolve_niche_from_discovery(
        discovery_f3iche="manufacturing",
        discovery_industry="General manufacturing",
        chat_transcript="user: We do on-site installation projects for commercial floors",
        niche_ids=NICHE_IDS,
    )
    assert niche == "manufacturing_project_chemical"


def test_specific_niche_passthrough():
    niche = resolve_niche_from_discovery(
        discovery_f3iche="manufacturing_garment_variants",
        niche_ids=NICHE_IDS,
    )
    assert niche == "manufacturing_garment_variants"


def test_discovery_evidence_bullets():
    bullets = discovery_evidence_bullets(
        discovery_f3iche="manufacturing",
        discovery_industry="Chemical coatings",
        chat_transcript="user: We manufacture epoxy coatings",
    )
    assert any("Chemical" in b for b in bullets)
    assert any("manufacturing" in b for b in bullets)


def test_generic_wip_pain_does_not_invent_a_specific_niche():
    niche = resolve_niche_from_text(
        "Lack of visibility into Work-In-Progress and production schedules",
        NICHE_IDS,
    )
    assert niche is None


def test_resolve_niche_from_text_chemical_message():
    niche = resolve_niche_from_text(
        "We manufacture epoxy floor coatings and run installation projects",
        NICHE_IDS,
    )
    assert niche == "manufacturing_project_chemical"
