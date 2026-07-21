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
    assert "ARCHETYPE HINTS" in ctx


def test_signal_ranked_hints_prioritize_match():
    """Planner context uses top signal-ranked archetypes, not full catalog dump."""
    ctx = asyncio.run(
        build_bottleneck_hint_context("incoming inspection ISO quality gate", f3iche_id=CHEMICAL_F3ICHE)
    )
    assert "incoming_quality_compliance" in ctx
    assert "TOP MATCHED REFERENCE PATTERNS" in ctx


def test_transcript_ranking_surfaces_factory_wip():
    transcript = (
        "Our factory floor is a black box because of yield variance. "
        "We need machine time at each step of the routing process."
    )
    ctx = asyncio.run(
        build_bottleneck_hint_context(
            "yield variance and costing",
            f3iche_id=CHEMICAL_F3ICHE,
            transcript=transcript,
        )
    )
    assert "factory_wip_bridge" in ctx
