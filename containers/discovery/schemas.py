"""Pydantic contracts for discovery LLM outputs (stable handoff to IS)."""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

COVERAGE_DIMENSION_KEYS = (
    "industry",
    "strategy",
    "scale",
    "legacy_system",
    "pain_point",
)


class CoverageDimension(BaseModel):
    status: Optional[Literal["confirmed", "partial"]] = None
    value: Optional[str] = None


class DiscoveryCoverage(BaseModel):
    industry: CoverageDimension = Field(default_factory=CoverageDimension)
    strategy: CoverageDimension = Field(default_factory=CoverageDimension)
    scale: CoverageDimension = Field(default_factory=CoverageDimension)
    legacy_system: CoverageDimension = Field(default_factory=CoverageDimension)
    pain_point: CoverageDimension = Field(default_factory=CoverageDimension)


class TranscriptExtractionResult(BaseModel):
    coverage: DiscoveryCoverage = Field(default_factory=DiscoveryCoverage)
    f3iche_hint: Optional[Literal["trading", "manufacturing", "service"]] = None
    industry_hint: Optional[str] = None


class MvpFocus(BaseModel):
    primary_bottleneck: str = ""
    functional_requirements: list[str] = Field(default_factory=list)
    archetype_id: Optional[str] = None
    defer_modules_mentioned: list[str] = Field(default_factory=list)


class RecommendationResult(BaseModel):
    recommended_erp: str = ""
    fit_score: int = 0
    headline: str = ""
    reasoning: str = ""
    f3iche: Literal["trading", "manufacturing", "service"] = "trading"
    industry: str = ""
    price_plan: Literal["Starter", "Standard", "Enterprise"] = "Standard"
    mvp_focus: MvpFocus = Field(default_factory=MvpFocus)


def _empty_coverage_dimension() -> dict[str, None]:
    return {"status": None, "value": None}


def coerce_extraction_raw(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalize LLM extract JSON before Pydantic validation."""
    out = dict(raw)
    coverage = dict(out.get("coverage") or {})
    for dim in COVERAGE_DIMENSION_KEYS:
        entry = coverage.get(dim)
        if entry is None or not isinstance(entry, dict):
            coverage[dim] = _empty_coverage_dimension()
    out["coverage"] = coverage
    return out


def coerce_recommendation_raw(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalize LLM recommend JSON before Pydantic validation."""
    out = dict(raw)
    focus = dict(out.get("mvp_focus") or {})
    if focus.get("functional_requirements") is None:
        focus["functional_requirements"] = []
    if focus.get("defer_modules_mentioned") is None:
        focus["defer_modules_mentioned"] = []
    out["mvp_focus"] = focus
    return out
