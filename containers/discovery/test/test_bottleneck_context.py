"""Tests for merged bottleneck hint context (interim catalog scaling)."""

from __future__ import annotations

import asyncio

from containers.discovery.bottleneck_context import build_bottleneck_hint_context

CHEMICAL_F3ICHE = "manufacturing_project_chemical"


def test_merged_hints_include_catalog_and_f3iche():
    ctx = asyncio.run(
        build_bottleneck_hint_context("WIP black box", f3iche_id=CHEMICAL_F3ICHE)
    )
    assert "factory_wip_bridge" in ctx
    assert "custom_order_pipeline" in ctx
    assert "ARCHETYPE HINTS" in ctx


def test_merged_hints_not_either_or():
    """Global-only archetype must appear even when F3iche has bottlenecks[]."""
    ctx = asyncio.run(
        build_bottleneck_hint_context("incoming inspection ISO quality gate", f3iche_id=CHEMICAL_F3ICHE)
    )
    assert "incoming_quality_compliance" in ctx
    assert "inventory_visibility" in ctx
