"""
Discovery Chat Service — synchronous ChatGPT-style conversation.

No Temporal, no per-turn coverage extraction, no polling.
Messages are stored in hooks.chat_history; structured output runs at /complete.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

from containers.discovery.prompts import (
    ADI_CHAT_SYSTEM_PROMPT,
    OPENING_MESSAGE,
    RECOMMENDATION_PROMPT,
    TRANSCRIPT_EXTRACTION_PROMPT,
)

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


def normalize_messages(chat_history: Any) -> list[dict]:
    """Accept legacy shapes; always return [{role, content, ts?}, ...]."""
    if not chat_history:
        return []
    if isinstance(chat_history, list):
        return [m for m in chat_history if isinstance(m, dict) and m.get("role") and m.get("content")]
    if isinstance(chat_history, dict):
        msgs = chat_history.get("messages")
        if isinstance(msgs, list):
            return normalize_messages(msgs)
    return []


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


def transcript_text(messages: list[dict]) -> str:
    lines = []
    for m in messages:
        role = m.get("role", "unknown").capitalize()
        content = (m.get("content") or "").strip()
        if content:
            lines.append(f"{role}: {content}")
    return "\n".join(lines)


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
    """Convert stored history to (role, content) tuples for llm_router."""
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


async def generate_chat_reply(messages: list[dict]) -> str:
    """Plain-text Adi reply given full conversation history."""
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
    """One-shot structured extraction from the full conversation."""
    from llm_router import invoke_smart_llm

    prompt = TRANSCRIPT_EXTRACTION_PROMPT.format(transcript=transcript_text(messages))
    response = await invoke_smart_llm(
        [("human", prompt)],
        model_name=DISCOVERY_EXTRACT_MODEL,
        temperature=EXTRACT_TEMPERATURE,
        max_output_tokens=800,
        response_mime_type="application/json",
    )
    result = _parse_llm_json(response.content)

    coverage = result.get("coverage") or {}
    # Merge with empty defaults; sanitize null values
    merged = {dim: dict(EMPTY_COVERAGE[dim]) for dim in EMPTY_COVERAGE}
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

    tags = result.get("extracted_tags") or []
    if not isinstance(tags, list):
        tags = []

    return {
        "coverage": merged,
        "extracted_tags": tags,
        "f3iche_hint": result.get("f3iche_hint"),
        "industry_hint": result.get("industry_hint"),
    }


async def generate_erp_recommendation(coverage: dict, tags: list) -> dict:
    """Generate ERP recommendation from extracted coverage + tags."""
    from llm_router import invoke_smart_llm

    tag_str = ", ".join(tags) if tags else "none"
    coverage_summary = _build_coverage_summary(coverage)
    primary_bottleneck = (coverage.get("pain_point") or {}).get("value") or ""

    rag_context = ""
    if primary_bottleneck:
        try:
            from containers.implementation.utils.rag_helper import rag_retrieve
            chunks = await rag_retrieve(primary_bottleneck, "business_bottlenecks", top_k=2)
            rag_context = "\n\n".join(chunks)
        except Exception as e:
            print(f"⚠️ RAG Retrieval failed for bottleneck: {e!r}")
            try:
                base_dir = os.path.dirname(os.path.abspath(__file__))
                map_path = os.path.join(base_dir, "..", "knowledge_base", "common", "mvp_bottleneck_map.json")
                if os.path.exists(map_path):
                    with open(map_path, "r") as f:
                        rag_context = f"FALLBACK MAP:\n{f.read()}"
            except Exception:
                pass

    formatted_prompt = RECOMMENDATION_PROMPT.format(
        extracted_tags=tag_str,
        coverage_summary=coverage_summary,
        rag_context=rag_context,
    )

    try:
        response = await invoke_smart_llm(
            [("human", formatted_prompt)],
            model_name=DISCOVERY_EXTRACT_MODEL,
            temperature=EXTRACT_TEMPERATURE,
            max_output_tokens=1000,
            response_mime_type="application/json",
        )
        return _parse_llm_json(response.content)
    except Exception as e:
        print(f"❌ Recommendation Error: {e!r}")
        industry_val = (coverage.get("industry") or {}).get("value") or ""
        is_mfg = "manufactur" in industry_val.lower()
        return {
            "recommended_erp": (
                "ERPNext Manufacturing (Standard)" if is_mfg else "ERPNext Distribution & Commerce"
            ),
            "fit_score": 78,
            "headline": "Strong Match for Your Business Profile",
            "reasoning": (
                "Based on your profile, ERPNext covers your core operational needs out of the box. "
                "We can tailor the configuration to your specific pain points."
            ),
            "f3iche": "manufacturing" if is_mfg else "trading",
            "industry": industry_val or "General",
            "price_plan": "Standard",
        }


async def complete_discovery(messages: list[dict]) -> dict:
    """Extract signals from transcript + generate recommendation."""
    extraction = await extract_from_transcript(messages)
    coverage = extraction["coverage"]
    tags = extraction["extracted_tags"]
    recommendation = await generate_erp_recommendation(coverage, tags)

    metadata = {
        "f3iche": recommendation.get("f3iche", "trading"),
        "industry": recommendation.get("industry", ""),
        "price_plan": recommendation.get("price_plan", "Standard"),
        "recommended_erp": recommendation.get("recommended_erp"),
        "fit_score": recommendation.get("fit_score"),
        "headline": recommendation.get("headline"),
        "reasoning": recommendation.get("reasoning"),
        "mvp_focus": recommendation.get("mvp_focus"),
    }

    return {
        "coverage": coverage,
        "extracted_tags": tags,
        "recommendation": recommendation,
        "discovery_metadata": metadata,
    }
