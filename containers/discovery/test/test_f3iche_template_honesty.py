"""Tests for honest F3iche template resolution (no silent cross-niche fallback)."""

from __future__ import annotations

from containers.discovery.niche_resolver import (
    f3iche_template_exists,
    f3iche_template_path,
    f3iche_template_status,
    resolve_discovery_f3iche_niche,
)


def test_trading_niche_resolves_without_manufacturing_substitution():
    niche = resolve_discovery_f3iche_niche(
        discovery_f3iche="trading",
        industry="FMCG wholesale distributor",
        chat_transcript="We distribute packaged goods to retailers.",
    )
    assert niche == "trading_fmcg_distributor"
    assert not f3iche_template_exists(niche)
    assert "trading_fmcg_distributor" in f3iche_template_path(niche).name
    assert "manufacturing" not in f3iche_template_path(niche).name


def test_f3iche_template_status_reports_missing_template():
    status = f3iche_template_status("trading_fmcg_distributor")
    assert status["template_available"] is False
    assert status["broad_category"] == "trading"


def test_manufacturing_niche_has_template():
    niche = resolve_discovery_f3iche_niche(
        discovery_f3iche="manufacturing",
        industry="industrial adhesives",
        chat_transcript="Apex Resins batch traceability chemical drums",
    )
    assert f3iche_template_exists(niche)
