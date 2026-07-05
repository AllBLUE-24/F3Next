"""Tests for discovery complete pipeline ordering (Phase 2)."""

from __future__ import annotations

import asyncio

from containers.discovery.chat_service import complete_discovery


def test_complete_discovery_passes_niche_to_recommend_hints(monkeypatch):
    hint_calls: list[str | None] = []

    async def mock_extract(messages):
        return {
            "coverage": {
                "industry": {"value": "epoxy coatings", "status": "confirmed"},
                "pain_point": {"value": "WIP black box", "status": "confirmed"},
                "strategy": {"status": None, "value": None},
                "scale": {"status": None, "value": None},
                "legacy_system": {"status": None, "value": None},
            },
            "f3iche_hint": "manufacturing",
            "industry_hint": "epoxy coatings",
        }

    async def mock_recommend(coverage, *, f3iche_hint=None, industry_hint=None, f3iche_id=None):
        hint_calls.append(f3iche_id)
        return {
            "recommended_erp": "ERPNext Manufacturing",
            "fit_score": 90,
            "headline": "Test",
            "reasoning": "Test",
            "f3iche": "manufacturing",
            "industry": "epoxy",
            "price_plan": "Standard",
            "mvp_focus": {
                "primary_bottleneck": "WIP",
                "functional_requirements": ["wip_tracking"],
                "archetype_id": "factory_wip_bridge",
            },
        }

    monkeypatch.setattr("containers.discovery.chat_service.extract_from_transcript", mock_extract)
    monkeypatch.setattr("containers.discovery.chat_service.generate_erp_recommendation", mock_recommend)

    messages = [
        {"role": "assistant", "content": "Hi"},
        {"role": "user", "content": "We make epoxy coatings with WIP black box."},
    ]

    result = asyncio.run(complete_discovery(messages, use_llm_niche=False))

    assert hint_calls == ["manufacturing_project_chemical"]
    assert result["f3iche_niche"] == "manufacturing_project_chemical"
    assert result["niche_resolution_source"] == "keyword"
    assert result["discovery_metadata"]["f3iche_niche"] == "manufacturing_project_chemical"
