"""Tests for discovery LLM output schema coercion (Phase 4)."""

from __future__ import annotations

import pytest

from containers.discovery.schemas import (
    RecommendationResult,
    TranscriptExtractionResult,
    coerce_extraction_raw,
    coerce_recommendation_raw,
)


def test_coerce_extraction_null_dimensions():
    raw = {
        "coverage": {
            "industry": {"value": "epoxy coatings", "status": "confirmed"},
            "strategy": None,
            "scale": None,
            "legacy_system": None,
            "pain_point": {"value": "WIP black box", "status": "confirmed"},
        },
        "f3iche_hint": "manufacturing",
    }
    coerced = coerce_extraction_raw(raw)
    parsed = TranscriptExtractionResult.model_validate(coerced)
    assert parsed.coverage.industry.value == "epoxy coatings"
    assert parsed.coverage.strategy.value is None
    assert parsed.coverage.legacy_system.value is None


def test_coerce_recommendation_defer_modules():
    raw = {
        "recommended_erp": "ERPNext",
        "fit_score": 80,
        "headline": "h",
        "reasoning": "r",
        "f3iche": "manufacturing",
        "industry": "coating",
        "price_plan": "Standard",
        "mvp_focus": {
            "primary_bottleneck": "custom orders",
            "functional_requirements": ["order_tracking"],
            "archetype_id": "factory_wip_bridge",
            "defer_modules_mentioned": ["Work Order", "Job Card"],
        },
    }
    coerced = coerce_recommendation_raw(raw)
    parsed = RecommendationResult.model_validate(coerced)
    assert parsed.mvp_focus.defer_modules_mentioned == ["Work Order", "Job Card"]


def test_coerce_recommendation_null_lists():
    raw = {
        "recommended_erp": "ERPNext",
        "fit_score": 80,
        "headline": "h",
        "reasoning": "r",
        "f3iche": "trading",
        "industry": "retail",
        "price_plan": "Starter",
        "mvp_focus": {
            "primary_bottleneck": "stockouts",
            "functional_requirements": None,
            "defer_modules_mentioned": None,
        },
    }
    coerced = coerce_recommendation_raw(raw)
    parsed = RecommendationResult.model_validate(coerced)
    assert parsed.mvp_focus.functional_requirements == []
    assert parsed.mvp_focus.defer_modules_mentioned == []
