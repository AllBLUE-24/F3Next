"""
Offline MVP plan draft + validate — no LLM required.

Used for golden tests, harness --planner-offline, and planner fallback when LLM fails.
Starts from signal/archetype hints (legacy classifier output) then validator corrects scope.
"""

from __future__ import annotations

from typing import Any, Optional

from containers.discovery.archetype_registry import (
    best_signal_match,
    get_by_id,
    signal_match_rankings,
)
from containers.discovery.mvp_validator import validate_mvp_plan
from containers.discovery.mvp_scoping import scope_mvp_seeds
from containers.discovery.niche_resolver import (
    infer_broad_f3iche,
    resolve_discovery_f3iche_niche,
    f3iche_template_path,
)
from containers.discovery.schemas import DoctypePlanEntry, MVPPlanResult
from containers.discovery.target.f3iche_seeds import load_f3iche_template_seeds


def _transcript_has_recall_batch_pain(transcript: str) -> bool:
    lower = transcript.lower()
    recall = any(
        kw in lower
        for kw in (
            "which other customers",
            "which customers received",
            "defective",
            "raw material batch",
            "trace which",
            "same bad batch",
        )
    )
    batch = any(kw in lower for kw in ("batch", "traceability", "expiry", "shelf life"))
    return recall and batch


def _resolve_offline_archetype_id(
    transcript: str,
    f3iche_id: str,
    mvp_focus: dict[str, Any],
) -> Optional[str]:
    if mvp_focus.get("archetype_id"):
        return str(mvp_focus["archetype_id"])

    if _transcript_has_recall_batch_pain(transcript):
        for preferred in ("batch_expiration_obsolescence", "inventory_visibility"):
            if get_by_id(preferred, f3iche_id):
                return preferred

    rankings = signal_match_rankings(transcript, f3iche_id, top_k=3)
    if rankings:
        top_id = rankings[0]["archetype_id"]
        if top_id == "incoming_quality_compliance" and _transcript_has_recall_batch_pain(transcript):
            return "batch_expiration_obsolescence"
        return top_id

    hit = best_signal_match(transcript, f3iche_id)
    if hit:
        return str(hit[0].get("archetype_id") or "")
    return None


def _legacy_system(coverage: dict[str, Any] | None) -> str:
    if not coverage:
        return ""
    return str((coverage.get("legacy_system") or {}).get("value") or "")


def _pain_point(coverage: dict[str, Any] | None, transcript: str) -> str:
    if coverage:
        val = (coverage.get("pain_point") or {}).get("value")
        if val:
            return str(val)
    return transcript[:200]


def draft_mvp_plan_offline(
    *,
    transcript: str,
    coverage: dict[str, Any] | None = None,
    broad_f3iche: str = "manufacturing",
    industry: str = "",
    mvp_focus: dict[str, Any] | None = None,
) -> MVPPlanResult:
    """
    Build a draft Day-1 plan without LLM.

    Uses niche resolver + archetype signal match for initial seeds (legacy path),
    then returns a plan object ready for validate_mvp_plan().
    """
    niche_id = resolve_discovery_f3iche_niche(
        discovery_f3iche=broad_f3iche,
        industry=industry,
        chat_transcript=transcript,
    )

    template_seeds, f3iche_data = load_f3iche_template_seeds(str(f3iche_template_path(niche_id)))

    focus = dict(mvp_focus or {})
    archetype_id = _resolve_offline_archetype_id(transcript, niche_id, focus)
    if archetype_id:
        focus["archetype_id"] = archetype_id
        entry = get_by_id(archetype_id, niche_id)
        if entry and not focus.get("primary_bottleneck"):
            focus["primary_bottleneck"] = str(entry.get("primary_bottleneck") or "")

    scoping = scope_mvp_seeds(
        template_seeds=template_seeds,
        f3iche_id=niche_id,
        f3iche_data=f3iche_data,
        mvp_focus=focus if focus.get("archetype_id") else None,
        coverage=coverage,
        chat_transcript=transcript,
    )

    day1 = scoping["mvp_seeds"]
    deferred = scoping["deferred_seeds"]
    legacy = _legacy_system(coverage)
    dual_note = scoping.get("dual_system_note") or ""
    if legacy and any(x in legacy.lower() for x in ("tally", "busy")) and not dual_note:
        dual_note = (
            "Accounting stays in your current system; ERPNext Day-1 focuses on "
            "factory/operations data that Tally cannot see."
        )

    return MVPPlanResult(
        niche_id=niche_id,
        niche_reasoning=f"Resolved from transcript keywords to {niche_id}.",
        primary_bottleneck=focus.get("primary_bottleneck") or _pain_point(coverage, transcript),
        workflows_required=[],
        day1_doctypes=[DoctypePlanEntry(doctype=dt, why="Archetype/signal scoping hint") for dt in day1],
        deferred_doctypes=[DoctypePlanEntry(doctype=dt, why="Deferred by template scoping") for dt in deferred],
        dual_system_note=dual_note,
        reference_archetype_ids=[scoping["archetype_id"]] if scoping.get("archetype_id") else [],
        plan_reasoning=scoping.get("scoping_reasoning") or "Offline draft from archetype scoping.",
        industry=industry or "Manufacturing",
        f3iche=broad_f3iche if broad_f3iche in ("trading", "manufacturing", "service") else "manufacturing",
        recommended_erp="ERPNext Manufacturing (Standard)",
        fit_score=80,
        headline="Day-1 MVP scoped to your operational bottleneck",
        reasoning=scoping.get("scoping_reasoning") or "",
        price_plan="Standard",
    )


def finalize_offline_mvp_plan(
    *,
    transcript: str,
    coverage: dict[str, Any] | None = None,
    industry: str = "",
    f3iche_hint: Optional[str] = None,
    mvp_focus: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Full offline pipeline: draft → validate → mvp_focus compatible with build_target.

    Returns same shape as plan_day1_mvp() for drop-in use in tests and harness.
    """
    broad = infer_broad_f3iche(f3iche_hint=f3iche_hint, industry=industry, coverage=coverage)
    plan = draft_mvp_plan_offline(
        transcript=transcript,
        coverage=coverage,
        broad_f3iche=broad,
        industry=industry,
        mvp_focus=mvp_focus,
    )

    niche_id = plan.niche_id
    template_seeds, _ = load_f3iche_template_seeds(str(f3iche_template_path(niche_id)))

    validation = validate_mvp_plan(
        day1_entries=[e.model_dump() for e in plan.day1_doctypes],
        deferred_entries=[e.model_dump() for e in plan.deferred_doctypes],
        niche_id=niche_id,
        chat_transcript=transcript,
        template_seeds=template_seeds,
        legacy_system=_legacy_system(coverage),
    )

    day1_names = validation.day1_doctypes
    deferred_names = validation.deferred_doctypes

    ref_arch = plan.reference_archetype_ids[0] if plan.reference_archetype_ids else None
    functional_requirements: list[str] = []
    if ref_arch:
        archetype = get_by_id(ref_arch, niche_id)
        if archetype:
            functional_requirements = list(archetype.get("functional_requirements") or [])

    mvp_focus_out = {
        "primary_bottleneck": plan.primary_bottleneck,
        "functional_requirements": functional_requirements,
        "archetype_id": ref_arch,
        "defer_modules_mentioned": deferred_names,
        "planner_day1_seeds": day1_names,
        "plan_reasoning": plan.plan_reasoning,
        "promoted_doctypes": validation.promoted_doctypes,
    }

    return {
        "plan": plan.model_dump(),
        "validation": validation.to_dict(),
        "mvp_focus": mvp_focus_out,
        "f3iche_niche": niche_id,
        "niche_resolution_source": "offline_draft",
        "day1_doctypes": day1_names,
        "deferred_doctypes": deferred_names,
        "promoted_doctypes": validation.promoted_doctypes,
        "dual_system_note": plan.dual_system_note,
        "plan_reasoning": plan.plan_reasoning,
        "recommendation": {
            "recommended_erp": plan.recommended_erp,
            "fit_score": plan.fit_score,
            "headline": plan.headline,
            "reasoning": plan.reasoning,
            "f3iche": plan.f3iche,
            "industry": plan.industry,
            "price_plan": plan.price_plan,
            "mvp_focus": mvp_focus_out,
        },
    }


__all__ = ["draft_mvp_plan_offline", "finalize_offline_mvp_plan"]
