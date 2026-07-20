"""
Discovery Step 1 MVP Planner — reason about transcript, validate against ERPNext graph.

Replaces archetype-id → day1_seed_hints lookup when DISCOVERY_USE_MVP_PLANNER is enabled.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Optional

from containers.discovery.archetype_registry import list_archetype_ids, get_by_id
from containers.discovery.bottleneck_context import build_bottleneck_hint_context
from containers.discovery.mvp_validator import (
    validate_mvp_plan,
    validation_errors_for_planner,
)
from containers.discovery.niche_resolver import list_f3iche_template_ids
from containers.discovery.prompts.planner import (
    MVP_PLANNER_PROMPT,
    MVP_PLANNER_REVISION_PROMPT,
)
from containers.discovery.schemas import MVPPlanResult, coerce_mvp_plan_raw
from containers.discovery.target.f3iche_seeds import load_f3iche_template_seeds
from containers.discovery.niche_resolver import f3iche_template_path

logger = logging.getLogger(__name__)

_USE_PLANNER = os.getenv("DISCOVERY_USE_MVP_PLANNER", "true").lower() not in (
    "0", "false", "no",
)
_PLANNER_MODEL = os.getenv("DISCOVERY_PLANNER_MODEL", os.getenv("DISCOVERY_EXTRACT_MODEL", "gpt-4o-mini"))
_PLANNER_TEMPERATURE = float(os.getenv("DISCOVERY_PLANNER_TEMPERATURE", "0.2"))
_MAX_REVISIONS = int(os.getenv("DISCOVERY_PLANNER_MAX_REVISIONS", "1"))

_GRAPH_PATH = (
    Path(__file__).parent.parent / "knowledge_base" / "erpnext" / "erpnext_doctype_graph.json"
)
_F3ICHE_DIR = Path(__file__).parent.parent / "knowledge_base" / "common" / "f3iches"


def planner_enabled() -> bool:
    return _USE_PLANNER


def _parse_llm_json(content: str) -> dict:
    start_idx = content.find("{")
    end_idx = content.rfind("}")
    if start_idx != -1 and end_idx != -1:
        clean_json = content[start_idx : end_idx + 1]
    else:
        clean_json = content.replace("```json", "").replace("```", "").strip()
    return json.loads(clean_json)


def _load_graph() -> dict[str, Any]:
    with open(_GRAPH_PATH, encoding="utf-8") as f:
        return json.load(f)


def _niche_catalog_summary() -> str:
    lines: list[str] = []
    for niche_id in list_f3iche_template_ids():
        path = _F3ICHE_DIR / f"{niche_id}.json"
        if not path.exists():
            lines.append(f"- {niche_id}")
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            display = data.get("display_name") or niche_id
            lines.append(f"- {niche_id}: {display}")
        except Exception:
            lines.append(f"- {niche_id}")
    return "\n".join(lines[:40])


def _graph_summary() -> str:
    graph = _load_graph()
    key_dts = [
        "Batch", "Item", "Stock Entry", "Delivery Note", "Customer",
        "Supplier", "Purchase Receipt", "Warehouse", "Work Order", "BOM",
    ]
    lines: list[str] = []
    for dt in key_dts:
        info = graph.get("doctypes", {}).get(dt, {})
        deps = info.get("depends_on") or []
        req = info.get("required_fields") or []
        if info:
            lines.append(f"- {dt}: depends_on={deps}; required_fields={req}")
    return "\n".join(lines)


def _coverage_summary(coverage: dict[str, Any]) -> str:
    lines: list[str] = []
    for dim in ("industry", "strategy", "scale", "legacy_system", "pain_point"):
        entry = coverage.get(dim) or {}
        val = entry.get("value")
        if val:
            lines.append(f"  • {dim}: {val}")
    return "\n".join(lines) if lines else "(none)"


def _legacy_system_value(coverage: dict[str, Any]) -> str:
    return str((coverage.get("legacy_system") or {}).get("value") or "")


async def _reference_patterns(primary_bottleneck: str, f3iche_id: Optional[str]) -> str:
    ctx = await build_bottleneck_hint_context(primary_bottleneck, f3iche_id=f3iche_id)
    return ctx or "(no patterns retrieved)"


def _plan_to_dict(plan: MVPPlanResult) -> dict[str, Any]:
    return plan.model_dump()


async def _invoke_planner_llm(prompt: str) -> dict[str, Any]:
    from llm_router import invoke_smart_llm

    response = await invoke_smart_llm(
        [("human", prompt)],
        model_name=_PLANNER_MODEL,
        temperature=_PLANNER_TEMPERATURE,
        max_output_tokens=2000,
        response_mime_type="application/json",
    )
    return coerce_mvp_plan_raw(_parse_llm_json(response.content))


async def plan_day1_mvp(
    *,
    transcript: str,
    coverage: dict[str, Any],
    broad_f3iche: str = "manufacturing",
    f3iche_id_hint: Optional[str] = None,
) -> dict[str, Any]:
    """
    Plan Day-1 MVP with LLM reasoning + deterministic validation.

    Falls back to offline draft+validate when LLM is unavailable.
    """
    legacy = _legacy_system_value(coverage)
    bottleneck = str((coverage.get("pain_point") or {}).get("value") or "")

    try:
        reference = await _reference_patterns(bottleneck, f3iche_id_hint)

        prompt = MVP_PLANNER_PROMPT.format(
            transcript=transcript[:8000],
            coverage_summary=_coverage_summary(coverage),
            legacy_system=legacy or "(none stated)",
            niche_catalog=_niche_catalog_summary(),
            reference_patterns=reference[:6000],
            graph_summary=_graph_summary(),
        )

        raw = await _invoke_planner_llm(prompt)
        plan = MVPPlanResult.model_validate(raw)
    except Exception as exc:
        logger.warning("MVP planner LLM failed, using offline draft+validate: %r", exc)
        from containers.discovery.mvp_plan_draft import finalize_offline_mvp_plan

        offline = finalize_offline_mvp_plan(
            transcript=transcript,
            coverage=coverage,
            industry=str((coverage.get("industry") or {}).get("value") or ""),
            f3iche_hint=broad_f3iche,
        )
        offline["niche_resolution_source"] = "planner_offline_fallback"
        return offline

    # Resolve template for validation allowlist
    niche_id = plan.niche_id or f3iche_id_hint or ""
    if not niche_id:
        niche_id = f"manufacturing_project_chemical" if broad_f3iche == "manufacturing" else broad_f3iche

    template_path = f3iche_template_path(niche_id)
    template_seeds, _ = load_f3iche_template_seeds(str(template_path))
    if not template_seeds:
        template_seeds = list_f3iche_template_ids()  # fallback minimal

    validation = validate_mvp_plan(
        day1_entries=[e.model_dump() for e in plan.day1_doctypes],
        deferred_entries=[e.model_dump() for e in plan.deferred_doctypes],
        niche_id=niche_id,
        chat_transcript=transcript,
        template_seeds=template_seeds,
        legacy_system=legacy,
    )

    revisions = 0
    while not validation.valid and revisions < _MAX_REVISIONS:
        revisions += 1
        logger.info("MVP planner revision %d — validation errors present", revisions)
        revision_prompt = MVP_PLANNER_REVISION_PROMPT.format(
            validation_errors=validation_errors_for_planner(validation),
            previous_plan=json.dumps(_plan_to_dict(plan), indent=2),
            transcript=transcript[:6000],
        )
        raw = await _invoke_planner_llm(revision_prompt)
        plan = MVPPlanResult.model_validate(raw)
        niche_id = plan.niche_id or niche_id
        template_path = f3iche_template_path(niche_id)
        template_seeds, _ = load_f3iche_template_seeds(str(template_path))
        validation = validate_mvp_plan(
            day1_entries=[e.model_dump() for e in plan.day1_doctypes],
            deferred_entries=[e.model_dump() for e in plan.deferred_doctypes],
            niche_id=niche_id,
            chat_transcript=transcript,
            template_seeds=template_seeds or [],
            legacy_system=legacy,
        )

    # Apply validator promotions to plan seeds
    day1_names = validation.day1_doctypes
    deferred_names = validation.deferred_doctypes

    # Build mvp_focus compatible with existing pipeline
    ref_arch = plan.reference_archetype_ids[0] if plan.reference_archetype_ids else None
    if ref_arch and ref_arch not in list_archetype_ids(niche_id):
        ref_arch = None

    functional_requirements: list[str] = []
    if ref_arch:
        archetype = get_by_id(ref_arch, niche_id)
        if archetype:
            functional_requirements = list(archetype.get("functional_requirements") or [])

    mvp_focus = {
        "primary_bottleneck": plan.primary_bottleneck or bottleneck,
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
        "mvp_focus": mvp_focus,
        "f3iche_niche": niche_id,
        "niche_resolution_source": "planner",
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
            "mvp_focus": mvp_focus,
        },
    }


__all__ = ["planner_enabled", "plan_day1_mvp"]
