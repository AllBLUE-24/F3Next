"""
Discovery Chat Service — synchronous ChatGPT-style conversation.

Messages are stored in hooks.chat_history; structured output runs at /complete.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional

from containers.discovery.bottleneck_context import build_bottleneck_hint_context
from containers.discovery.prompts import (
    ADI_CHAT_SYSTEM_PROMPT,
    OPENING_MESSAGE,
    RECOMMENDATION_PROMPT,
    TRANSCRIPT_EXTRACTION_PROMPT,
)
from containers.discovery.schemas import (
    RecommendationResult,
    TranscriptExtractionResult,
    coerce_extraction_raw,
    coerce_recommendation_raw,
)
from containers.discovery.recommend_guard import apply_recommend_guard
from containers.discovery.utils import normalize_messages, transcript_text

logger = logging.getLogger(__name__)

MAX_USER_TURNS = int(os.getenv("DISCOVERY_MAX_TURNS", "20"))
DISCOVERY_CHAT_MODEL = os.getenv("DISCOVERY_CHAT_MODEL", "gpt-4o-mini")
DISCOVERY_EXTRACT_MODEL = os.getenv("DISCOVERY_EXTRACT_MODEL", "gpt-4o-mini")
CHAT_TEMPERATURE = float(os.getenv("DISCOVERY_CHAT_TEMPERATURE", "0.7"))
EXTRACT_TEMPERATURE = float(os.getenv("DISCOVERY_EXTRACT_TEMPERATURE", "0.1"))

_DIM_LABELS = {
    "industry": "Industry & business type",
    "strategy": "Fulfillment strategy",
    "scale": "Business scale",
    "legacy_system": "Current software / system",
    "pain_point": "Biggest operational challenge",
}

EMPTY_COVERAGE = {
    "industry": {"status": None, "value": None},
    "strategy": {"status": None, "value": None},
    "scale": {"status": None, "value": None},
    "legacy_system": {"status": None, "value": None},
    "pain_point": {"status": None, "value": None},
}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def opening_messages() -> list[dict]:
    return [
        {
            "role": "assistant",
            "content": OPENING_MESSAGE,
            "ts": _utc_now_iso(),
        }
    ]


def count_user_turns(messages: list[dict]) -> int:
    return sum(1 for m in messages if m.get("role") == "user")


def _build_coverage_summary(coverage: dict) -> str:
    lines = []
    for dim, label in _DIM_LABELS.items():
        entry = coverage.get(dim, {"status": None, "value": None})
        value = entry.get("value")
        if value:
            lines.append(f"  • {label}: {value}")
        else:
            lines.append(f"  • {label}: not mentioned")
    return "\n".join(lines)


def _parse_llm_json(content: str) -> dict:
    start_idx = content.find("{")
    end_idx = content.rfind("}")
    if start_idx != -1 and end_idx != -1:
        clean_json = content[start_idx : end_idx + 1]
    else:
        clean_json = content.replace("```json", "").replace("```", "").strip()
    return json.loads(clean_json)


def _to_langchain_messages(messages: list[dict]) -> list[tuple[str, str]]:
    lc: list[tuple[str, str]] = [("system", ADI_CHAT_SYSTEM_PROMPT)]
    for m in messages:
        role = m.get("role")
        content = (m.get("content") or "").strip()
        if not content:
            continue
        if role == "user":
            lc.append(("human", content))
        elif role == "assistant":
            lc.append(("ai", content))
    return lc


def _coverage_from_extraction(raw: dict[str, Any]) -> dict[str, dict]:
    merged = {dim: dict(EMPTY_COVERAGE[dim]) for dim in EMPTY_COVERAGE}
    coverage = raw.get("coverage") or {}
    for dim, entry in coverage.items():
        if dim not in merged or not isinstance(entry, dict):
            continue
        val = entry.get("value")
        status = entry.get("status")
        if val:
            merged[dim]["value"] = val
            merged[dim]["status"] = status if status in ("confirmed", "partial") else "confirmed"
        else:
            merged[dim] = {"status": None, "value": None}
    return merged


async def generate_chat_reply(messages: list[dict]) -> str:
    from llm_router import invoke_smart_llm

    lc_messages = _to_langchain_messages(messages)
    response = await invoke_smart_llm(
        lc_messages,
        model_name=DISCOVERY_CHAT_MODEL,
        temperature=CHAT_TEMPERATURE,
        max_output_tokens=400,
    )
    reply = (response.content or "").strip()
    if not reply:
        raise RuntimeError("Empty reply from discovery chat model")
    return reply


async def extract_from_transcript(messages: list[dict]) -> dict:
    from llm_router import invoke_smart_llm

    prompt = TRANSCRIPT_EXTRACTION_PROMPT.format(transcript=transcript_text(messages))
    response = await invoke_smart_llm(
        [("human", prompt)],
        model_name=DISCOVERY_EXTRACT_MODEL,
        temperature=EXTRACT_TEMPERATURE,
        max_output_tokens=800,
        response_mime_type="application/json",
    )
    raw = coerce_extraction_raw(_parse_llm_json(response.content))

    try:
        parsed = TranscriptExtractionResult.model_validate(raw)
        coverage = parsed.coverage.model_dump()
        f3iche_hint = parsed.f3iche_hint
        industry_hint = parsed.industry_hint
    except Exception as e:
        logger.warning("Extract schema validation failed, using raw: %s", e)
        coverage = _coverage_from_extraction(raw)
        f3iche_hint = raw.get("f3iche_hint")
        industry_hint = raw.get("industry_hint")

    return {
        "coverage": coverage,
        "f3iche_hint": f3iche_hint,
        "industry_hint": industry_hint,
    }


async def generate_erp_recommendation(
    coverage: dict,
    *,
    f3iche_hint: Optional[str] = None,
    industry_hint: Optional[str] = None,
    f3iche_id: Optional[str] = None,
) -> dict:
    from llm_router import invoke_smart_llm

    coverage_summary = _build_coverage_summary(coverage)
    primary_bottleneck = (coverage.get("pain_point") or {}).get("value") or ""

    bottleneck_hint_context = await build_bottleneck_hint_context(
        primary_bottleneck,
        f3iche_id=f3iche_id,
    )

    formatted_prompt = RECOMMENDATION_PROMPT.format(
        coverage_summary=coverage_summary,
        bottleneck_hint_context=bottleneck_hint_context,
    )

    try:
        response = await invoke_smart_llm(
            [("human", formatted_prompt)],
            model_name=DISCOVERY_EXTRACT_MODEL,
            temperature=EXTRACT_TEMPERATURE,
            max_output_tokens=1000,
            response_mime_type="application/json",
        )
        raw = coerce_recommendation_raw(_parse_llm_json(response.content))
        try:
            result = RecommendationResult.model_validate(raw).model_dump()
        except Exception as e:
            logger.warning("Recommend schema validation failed: %s", e)
            result = raw
        return apply_recommend_guard(result, f3iche_id=f3iche_id)
    except Exception as e:
        logger.error("Recommendation LLM failed: %r", e)
        industry_val = (coverage.get("industry") or {}).get("value") or industry_hint or ""
        is_mfg = "manufactur" in industry_val.lower() or f3iche_hint == "manufacturing"
        return RecommendationResult(
            recommended_erp=(
                "ERPNext Manufacturing (Standard)" if is_mfg else "ERPNext Distribution & Commerce"
            ),
            fit_score=78,
            headline="Strong Match for Your Business Profile",
            reasoning=(
                "Based on your profile, ERPNext covers your core operational needs out of the box. "
                "We can tailor the configuration to your specific pain points."
            ),
            f3iche="manufacturing" if is_mfg else "trading",
            industry=industry_val or "General",
            price_plan="Standard",
        ).model_dump()


async def complete_discovery(
    messages: list[dict],
    *,
    use_llm_niche: Optional[bool] = None,
    clarification_answers: dict[str, Any] | None = None,
    transcript_override: str | None = None,
) -> dict:
    """Extract signals, resolve niche, then plan or recommend Day-1 MVP."""
    from containers.discovery.discovery_clarify import append_clarifications_to_transcript
    from containers.discovery.mvp_planner import plan_day1_mvp, planner_enabled
    from containers.discovery.niche_resolver import (
        infer_broad_f3iche,
        resolve_discovery_f3iche_niche_async,
    )

    extraction = await extract_from_transcript(messages)
    coverage = extraction["coverage"]
    chat_transcript = transcript_override or transcript_text(messages)
    if clarification_answers:
        chat_transcript = append_clarifications_to_transcript(
            chat_transcript, clarification_answers
        )

    industry = (
        (coverage.get("industry") or {}).get("value")
        or extraction.get("industry_hint")
        or ""
    )
    broad_f3iche = infer_broad_f3iche(
        f3iche_hint=extraction.get("f3iche_hint"),
        industry=industry,
        coverage=coverage,
    )

    if planner_enabled():
        planner_result = await plan_day1_mvp(
            transcript=chat_transcript,
            coverage=coverage,
            broad_f3iche=broad_f3iche,
        )
        recommendation = planner_result["recommendation"]
        niche_id = planner_result["f3iche_niche"]
        niche_source = planner_result["niche_resolution_source"]
        metadata = {
            "f3iche": recommendation.get("f3iche", broad_f3iche),
            "industry": recommendation.get("industry", industry),
            "price_plan": recommendation.get("price_plan", "Standard"),
            "recommended_erp": recommendation.get("recommended_erp"),
            "fit_score": recommendation.get("fit_score"),
            "headline": recommendation.get("headline"),
            "reasoning": recommendation.get("reasoning"),
            "mvp_focus": planner_result["mvp_focus"],
            "f3iche_niche": niche_id,
            "niche_resolution_source": niche_source,
            "mvp_plan": planner_result["plan"],
            "mvp_plan_validation": planner_result["validation"],
            "plan_reasoning": planner_result.get("plan_reasoning", ""),
            "dual_system_note": planner_result.get("dual_system_note", ""),
            "promoted_doctypes": planner_result.get("promoted_doctypes") or [],
            "scoping_mode": "planner_validated",
        }
        return {
            "coverage": coverage,
            "recommendation": recommendation,
            "discovery_metadata": metadata,
            "f3iche_niche": niche_id,
            "niche_resolution_source": niche_source,
            "broad_f3iche": broad_f3iche,
            "mvp_plan": planner_result,
        }

    niche_id, niche_source = await resolve_discovery_f3iche_niche_async(
        discovery_f3iche=broad_f3iche,
        industry=industry,
        chat_transcript=chat_transcript,
        coverage=coverage,
        use_llm_niche=use_llm_niche,
    )

    recommendation = await generate_erp_recommendation(
        coverage,
        f3iche_hint=extraction.get("f3iche_hint"),
        industry_hint=extraction.get("industry_hint"),
        f3iche_id=niche_id,
    )

    metadata = {
        "f3iche": recommendation.get("f3iche", broad_f3iche),
        "industry": recommendation.get("industry", industry),
        "price_plan": recommendation.get("price_plan", "Standard"),
        "recommended_erp": recommendation.get("recommended_erp"),
        "fit_score": recommendation.get("fit_score"),
        "headline": recommendation.get("headline"),
        "reasoning": recommendation.get("reasoning"),
        "mvp_focus": recommendation.get("mvp_focus"),
        "f3iche_niche": niche_id,
        "niche_resolution_source": niche_source,
    }

    return {
        "coverage": coverage,
        "recommendation": recommendation,
        "discovery_metadata": metadata,
        "f3iche_niche": niche_id,
        "niche_resolution_source": niche_source,
        "broad_f3iche": broad_f3iche,
    }
