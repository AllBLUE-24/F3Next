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


class DoctypePlanEntry(BaseModel):
    doctype: str
    why: str = ""


class MVPPlanResult(BaseModel):
    """Structured Day-1 MVP plan from the discovery planner (replaces classifier scope)."""

    niche_id: str = ""
    niche_reasoning: str = ""
    primary_bottleneck: str = ""
    workflows_required: list[str] = Field(default_factory=list)
    day1_doctypes: list[DoctypePlanEntry] = Field(default_factory=list)
    deferred_doctypes: list[DoctypePlanEntry] = Field(default_factory=list)
    dual_system_note: str = ""
    reference_archetype_ids: list[str] = Field(default_factory=list)
    plan_reasoning: str = ""
    industry: str = ""
    f3iche: Literal["trading", "manufacturing", "service"] = "manufacturing"
    recommended_erp: str = ""
    fit_score: int = 0
    headline: str = ""
    reasoning: str = ""
    price_plan: Literal["Starter", "Standard", "Enterprise"] = "Standard"


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
    aid = focus.get("archetype_id")
    if aid is not None:
        token = str(aid).strip().lower()
        if token in ("null", "none", "undefined", "n/a", ""):
            focus["archetype_id"] = None
    out["mvp_focus"] = focus
    return out


def coerce_mvp_plan_raw(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalize LLM planner JSON before Pydantic validation."""
    out = dict(raw)
    for key in ("day1_doctypes", "deferred_doctypes"):
        entries = out.get(key) or []
        normalized: list[dict[str, str]] = []
        for entry in entries:
            if isinstance(entry, str):
                normalized.append({"doctype": entry.strip(), "why": ""})
            elif isinstance(entry, dict):
                normalized.append({
                    "doctype": str(entry.get("doctype") or "").strip(),
                    "why": str(entry.get("why") or ""),
                })
        out[key] = normalized
    if out.get("workflows_required") is None:
        out["workflows_required"] = []
    if out.get("reference_archetype_ids") is None:
        out["reference_archetype_ids"] = []
    return out
