"""Tests for honest F3iche template resolution (no silent cross-niche fallback)."""

from __future__ import annotations

import asyncio

from containers.discovery.niche_resolver import (
    f3iche_template_exists,
    f3iche_template_path,
    f3iche_template_status,
    resolve_discovery_f3iche_niche,
)
from containers.discovery.target.build_target import build_discovery_target


def test_trading_niche_resolves_without_manufacturing_substitution():
    niche = resolve_discovery_f3iche_niche(
        discovery_f3iche="trading",
        industry="FMCG wholesale distributor",
        chat_transcript="We distribute packaged goods to retailers.",
    )
    assert niche == "trading_fmcg_distributor"
    assert f3iche_template_exists(niche)
    assert "trading_fmcg_distributor" in f3iche_template_path(niche).name
    assert "manufacturing" not in f3iche_template_path(niche).name


def test_field_service_resolves_to_service_professional():
    niche = resolve_discovery_f3iche_niche(
        discovery_f3iche="service",
        industry="HVAC field service",
        chat_transcript="Technicians get WhatsApp repair requests with no dispatch queue.",
    )
    assert niche == "service_professional"
    assert f3iche_template_exists(niche)


def test_f3iche_template_status_reports_missing_template():
    status = f3iche_template_status("trading_hardware_variants")
    assert status["template_available"] is False
    assert status["broad_category"] == "trading"


def test_manufacturing_niche_has_template():
    niche = resolve_discovery_f3iche_niche(
        discovery_f3iche="manufacturing",
        industry="industrial adhesives",
        chat_transcript="Apex Resins batch traceability chemical drums",
    )
    assert f3iche_template_exists(niche)


def test_build_target_degrades_cleanly_for_missing_trading_template():
    result = asyncio.run(
        build_discovery_target(
            f3iche="trading_hardware_variants",
            mvp_focus={
                "planner_day1_seeds": ["Item", "Customer", "Warehouse", "Delivery Note"],
            },
            chat_transcript="Hardware distributor pipe and steel trading",
        )
    )
    status = result["mvp_boundary"]["template_status"]
    assert status["template_available"] is False
    assert status["niche_id"] == "trading_hardware_variants"
    assert result["seed_doctypes"]
    assert "manufacturing" not in str(status.get("template_path", ""))
