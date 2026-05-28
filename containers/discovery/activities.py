import json
import re
from uuid import UUID

from temporalio import activity
from containers.discovery.prompts import ADI_SYSTEM_PROMPT, DISCOVERY_TURN_PROMPT, RECOMMENDATION_PROMPT
from containers.knowledge_base.common.discovery_taxonomy import KNOWLEDGE_BASE
from shared.database.db import engine
from shared.models.hooks import Hook
from sqlalchemy import update

# ------------------------------------------------------------------
# DEFAULTS
# ------------------------------------------------------------------
MAX_TURNS = 8

EMPTY_COVERAGE = {
    "industry":      {"status": None, "value": None},
    "strategy":      {"status": None, "value": None},
    "scale":         {"status": None, "value": None},
    "legacy_system": {"status": None, "value": None},
    "pain_point":    {"status": None, "value": None},
}

_DIM_LABELS = {
    "industry":      "what the company does",
    "strategy":      "how they fulfill orders",
    "scale":         "company size (turnover or headcount)",
    "legacy_system": "current software / tools",
    "pain_point":    "biggest operational challenge",
}

_GREETING_RE = re.compile(
    r"^(hi|hello|hey|hiya|howdy|yo|sup|namaste|good\s*(morning|afternoon|evening))[\s!.,?]*$",
    re.IGNORECASE,
)

_TURNOVER_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(cr|crore|crores|crs|lakh|lakhs|lac|lacs|million|mn|billion|bn)\b",
    re.IGNORECASE,
)

_HEADCOUNT_RE = re.compile(
    r"(\d+)\s*(?:\+?\s*)?(employee|employees|staff|people|team\s*members?|headcount|workers?)\b",
    re.IGNORECASE,
)

_LEGACY_KEYWORDS = {
    "tally":       "#Legacy_Tally",
    "excel":       "#Legacy_Excel",
    "spreadsheet": "#Legacy_Excel",
    "busy":        "#Legacy_Busy",
    "zoho":        "#Legacy_Zoho",
    "sap":         "#Legacy_SAP",
    "oracle":      "#Legacy_Oracle",
    "netsuite":    "#Legacy_Oracle",
    "custom erp":  "#Legacy_CustomERP",
    "in-house":    "#Legacy_CustomERP",
    "in house":    "#Legacy_CustomERP",
    "pen and paper": "#Legacy_None",
    "no system":   "#Legacy_None",
    "nothing":     "#Legacy_None",
}

# ------------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------------

def _build_coverage_summary(coverage: dict) -> str:
    """Full summary for recommendation prompt."""
    lines = []
    for dim, label in _DIM_LABELS.items():
        entry = coverage.get(dim, {"status": None, "value": None})
        status = entry.get("status")
        value = entry.get("value") or "unknown"
        if status in ("confirmed", "partial"):
            lines.append(f"  • {label}: {value} ({status})")
        else:
            lines.append(f"  • {label}: not yet known")
    return "\n".join(lines)


def _build_known_summary(coverage: dict) -> str:
    """Only confirmed/partial facts — for conversational context."""
    lines = []
    for dim, label in _DIM_LABELS.items():
        entry = coverage.get(dim, {"status": None, "value": None})
        if entry.get("status") in ("confirmed", "partial") and entry.get("value"):
            lines.append(f"  • {label}: {entry['value']}")
    return "\n".join(lines) if lines else "  (nothing yet — this is early in the conversation)"


def _build_gaps_summary(coverage: dict) -> str:
    """Only what's still missing — avoids checklist mentality in the prompt."""
    gaps = []
    for dim, label in _DIM_LABELS.items():
        entry = coverage.get(dim, {"status": None, "value": None})
        if entry.get("status") not in ("confirmed", "partial") or not entry.get("value"):
            gaps.append(f"  • {label}")
    return "\n".join(gaps) if gaps else "  (all covered — wrap up warmly, no new questions)"


def _merge_coverage(existing: dict, updated: dict) -> dict:
    result = {dim: dict(entry) for dim, entry in existing.items()}

    for dim, new_entry in updated.items():
        if dim not in result:
            continue
        if not isinstance(new_entry, dict):
            continue

        new_status = new_entry.get("status")
        new_value = new_entry.get("value")
        old_status = result[dim].get("status")

        if old_status == "confirmed" and new_status == "partial":
            continue

        if new_status is not None:
            result[dim]["status"] = new_status
        if new_value is not None:
            result[dim]["value"] = new_value

    return result


def _sanitize_coverage(coverage: dict) -> dict:
    for dim_key, dim_entry in coverage.items():
        if not isinstance(dim_entry, dict):
            coverage[dim_key] = {"status": None, "value": None}
        elif dim_entry.get("value") in (None, ""):
            dim_entry["status"] = None
    return coverage


def _coverage_is_complete(coverage: dict, turn: int) -> bool:
    filled = sum(
        1 for v in coverage.values()
        if isinstance(v, dict)
        and v.get("status") in ("partial", "confirmed")
        and v.get("value") not in (None, "")
    )
    return filled >= 5 or turn >= MAX_TURNS


def _is_greeting(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    if _GREETING_RE.match(stripped):
        return True
    # Very short non-substantive openers
    if len(stripped.split()) <= 2 and stripped.lower() in {
        "hi", "hello", "hey", "hii", "hiii", "helo", "hlw", "hlo",
    }:
        return True
    return False


def _scale_tag_for_crores(crores: float) -> str:
    if crores < 2:
        return "#Scale_Micro"
    if crores <= 50:
        return "#Scale_SMB"
    return "#Scale_Large"


def _to_crores(amount: float, unit: str) -> float:
    u = unit.lower()
    if u in ("cr", "crore", "crores", "crs"):
        return amount
    if u in ("lakh", "lakhs", "lac", "lacs"):
        return amount / 100.0
    if u in ("million", "mn"):
        return amount * 0.1  # 1M INR ≈ 0.1 Cr (rough; good enough for banding)
    if u in ("billion", "bn"):
        return amount * 100.0
    return amount


def _heuristic_extract(user_answer: str, coverage: dict) -> tuple[dict, list[str]]:
    """
    Deterministic pre-extraction for formats the LLM often misses.
    Returns (coverage_updates dict, tags list).
    """
    text = user_answer.strip()
    if not text:
        return {}, []

    updates: dict = {}
    tags: list[str] = []

    # --- Scale: turnover ---
    turnover_parts = []
    for match in _TURNOVER_RE.finditer(text):
        amount = float(match.group(1))
        unit = match.group(2)
        crores = _to_crores(amount, unit)
        turnover_parts.append(f"{match.group(1)} {match.group(2)}")
        tags.append(_scale_tag_for_crores(crores))

    # --- Scale: headcount ---
    headcount_parts = []
    for match in _HEADCOUNT_RE.finditer(text):
        headcount_parts.append(f"{match.group(1)} {match.group(2)}")

    if turnover_parts or headcount_parts:
        scale_value = ", ".join(filter(None, [
            f"Turnover ~{' / '.join(turnover_parts)}" if turnover_parts else None,
            f"Team of {' / '.join(headcount_parts)}" if headcount_parts else None,
        ]))
        existing_scale = coverage.get("scale", {})
        if existing_scale.get("status") != "confirmed":
            updates["scale"] = {"status": "confirmed", "value": scale_value}

    # --- Legacy system keywords ---
    lower = text.lower()
    for keyword, tag in _LEGACY_KEYWORDS.items():
        if keyword in lower:
            tags.append(tag)
            if coverage.get("legacy_system", {}).get("status") != "confirmed":
                updates["legacy_system"] = {
                    "status": "confirmed",
                    "value": keyword.title() if keyword != "in-house" else "In-house system",
                }
            break

    return updates, list(dict.fromkeys(tags))


def _apply_heuristics(user_answer: str, coverage: dict) -> tuple[dict, list[str]]:
    """Merge heuristic extraction into coverage."""
    updates, tags = _heuristic_extract(user_answer, coverage)
    if updates:
        coverage = _merge_coverage(coverage, updates)
        coverage = _sanitize_coverage(coverage)
    return coverage, tags


def _greeting_response(coverage: dict) -> str:
    known = _build_known_summary(coverage)
    has_any = "nothing yet" not in known

    if not has_any:
        return (
            "Hey! Good to meet you — I'm Adi. "
            "I help businesses figure out the right ERP setup. "
            "What does your company do?"
        )

    gaps = [
        label for dim, label in _DIM_LABELS.items()
        if coverage.get(dim, {}).get("status") not in ("confirmed", "partial")
        or not coverage.get(dim, {}).get("value")
    ]
    if gaps:
        return (
            f"Hey! Good to hear from you. "
            f"I've got a decent picture so far — could you tell me about {gaps[0]}?"
        )
    return (
        "Hey! I think we've covered the basics — "
        "anything else you'd like to add before I put together your recommendation?"
    )


def _contextual_fallback_response(
    coverage: dict, turn: int, user_answer: str, reason: str = "llm_fallback",
) -> dict:
    """
    Fallback when LLM fails — uses heuristics first, then a natural question
    that references conversation context instead of canned templates.
    """
    coverage, heuristic_tags = _apply_heuristics(user_answer, dict(coverage))
    coverage = _sanitize_coverage(coverage)

    if _is_greeting(user_answer):
        return {
            "status": "SUCCESS",
            "reason": reason,
            "answer_quality": "vague",
            "extracted_tags": heuristic_tags,
            "updated_coverage": coverage,
            "bot_response": _greeting_response(coverage),
            "is_complete": _coverage_is_complete(coverage, turn + 1),
            "f3iche_hint": None,
            "industry_hint": None,
        }

    gap_questions = {
        "industry":      "What does your company make, sell, or offer?",
        "strategy":      "Do you keep stock ready, or produce only when a customer orders?",
        "scale":         "Roughly what's your annual turnover or team size?",
        "legacy_system": "What do you use today for billing or inventory — Tally, Excel, something else?",
        "pain_point":    "What's the one operational headache that eats the most time?",
    }

    for dim in ["industry", "strategy", "scale", "legacy_system", "pain_point"]:
        entry = coverage.get(dim, {})
        if entry.get("status") not in ("confirmed", "partial") or not entry.get("value"):
            # Don't repeat scale question if user just gave numbers
            if dim == "scale" and _TURNOVER_RE.search(user_answer):
                continue
            return {
                "status": "SUCCESS",
                "reason": reason,
                "answer_quality": "vague",
                "extracted_tags": heuristic_tags,
                "updated_coverage": coverage,
                "bot_response": gap_questions[dim],
                "is_complete": _coverage_is_complete(coverage, turn + 1),
                "f3iche_hint": None,
                "industry_hint": None,
            }

    return {
        "status": "SUCCESS",
        "reason": "llm_fallback_complete",
        "answer_quality": "clear",
        "extracted_tags": heuristic_tags,
        "updated_coverage": coverage,
        "bot_response": (
            "Thanks — I think I have a solid picture of your business. "
            "Let me put together your ERP recommendation."
        ),
        "is_complete": True,
        "f3iche_hint": None,
        "industry_hint": None,
    }


def _parse_llm_json(content: str) -> dict:
    start_idx = content.find("{")
    end_idx = content.rfind("}")
    if start_idx != -1 and end_idx != -1:
        clean_json = content[start_idx:end_idx + 1]
    else:
        clean_json = content.replace("```json", "").replace("```", "").strip()
    return json.loads(clean_json)


async def _call_discovery_llm(
    coverage: dict,
    user_answer: str,
    conversation_history: list,
    accumulated_tags: list,
) -> dict:
    from llm_router import invoke_smart_llm

    formatted_prompt = DISCOVERY_TURN_PROMPT.format(
        known_summary=_build_known_summary(coverage),
        gaps_summary=_build_gaps_summary(coverage),
        conversation_history=(
            "\n".join(conversation_history[-12:]) if conversation_history else "(none yet)"
        ),
        user_answer=user_answer,
        accumulated_tags=", ".join(accumulated_tags) if accumulated_tags else "none yet",
    )

    response = await invoke_smart_llm([
        ("system", ADI_SYSTEM_PROMPT),
        ("human", formatted_prompt),
    ])
    return _parse_llm_json(response.content)


# ------------------------------------------------------------------
# ACTIVITIES
# ------------------------------------------------------------------

@activity.defn
async def analyze_discovery_turn(data: dict) -> dict:
    """
    Core intelligence activity. Pre-extracts heuristics, then calls LLM
    for signal extraction + natural reply.
    """
    user_answer = data.get("user_answer", "")
    current_coverage = dict(data.get("current_coverage") or EMPTY_COVERAGE)
    accumulated_tags = list(data.get("accumulated_tags") or [])
    conversation_history = data.get("conversation_history") or []
    turn_count = data.get("turn_count", 0)

    # 1. Heuristic pre-extraction (runs before LLM — fixes "120 cr" etc.)
    current_coverage, heuristic_tags = _apply_heuristics(user_answer, current_coverage)

    # 2. Greeting-only messages — respond naturally without LLM
    if _is_greeting(user_answer) and not heuristic_tags:
        bot_response = _greeting_response(current_coverage)
        return {
            "status": "SUCCESS",
            "reason": "greeting_handler",
            "answer_quality": "vague",
            "extracted_tags": [],
            "updated_coverage": current_coverage,
            "bot_response": bot_response,
            "message": bot_response,
            "is_complete": _coverage_is_complete(current_coverage, turn_count + 1),
            "f3iche_hint": None,
            "industry_hint": None,
        }

    # 3. LLM call with retry
    result = None
    last_error = None
    for attempt in range(2):
        try:
            result = await _call_discovery_llm(
                current_coverage, user_answer, conversation_history, accumulated_tags,
            )
            break
        except Exception as e:
            last_error = e
            print(f"⚠️ Adi LLM attempt {attempt + 1} failed (turn {turn_count}): {e!r}")

    if result is None:
        print(f"❌ Adi Activity Error (turn {turn_count}): {last_error!r}")
        fallback = _contextual_fallback_response(
            current_coverage, turn_count, user_answer,
        )
        fallback["message"] = fallback.get("bot_response", "")
        return fallback

    # 4. Merge LLM extraction on top of heuristic baseline
    llm_updated = result.get("updated_coverage") or {}
    merged_coverage = _merge_coverage(current_coverage, llm_updated)
    merged_coverage = _sanitize_coverage(merged_coverage)

    # Re-apply heuristics so code-extracted scale never gets wiped by LLM
    merged_coverage, extra_tags = _apply_heuristics(user_answer, merged_coverage)
    all_tags = list(dict.fromkeys(
        (result.get("extracted_tags") or []) + heuristic_tags + extra_tags
    ))

    result["updated_coverage"] = merged_coverage
    result["extracted_tags"] = all_tags
    result["message"] = result.get("bot_response", "")
    result["is_complete"] = _coverage_is_complete(merged_coverage, turn_count + 1)

    filled_dims = [
        dim for dim, v in merged_coverage.items()
        if isinstance(v, dict) and v.get("value")
    ]
    print(
        f"[Adi turn {turn_count}] filled={len(filled_dims)} {filled_dims} "
        f"| complete={result['is_complete']}"
    )

    return result


@activity.defn
async def save_discovery_state(data: dict):
    """Persists the current conversation state to the hooks table after each turn."""
    pid = data.get("project_id")
    if isinstance(pid, str):
        pid = UUID(pid)

    bot_text = data.get("message") or data.get("bot_response", "")
    coverage = data.get("coverage")
    turn_count = data.get("turn_count", 0)
    current_step = data.get("step", 1)
    tags = data.get("tags", [])

    is_complete = data.get("is_complete", False)

    async with engine.begin() as conn:
        await conn.execute(
            update(Hook)
            .where(Hook.project_id == pid)
            .values(
                last_bot_response=bot_text,
                discovery_step=current_step,
                extracted_tags=tags,
                discovery_coverage=coverage,
                discovery_turn_count=turn_count,
                discovery_status="COMPLETE" if is_complete else "PROCESSING",
            )
        )
    return True


@activity.defn
async def generate_erp_recommendation(data: dict) -> dict:
    """Final step: generate the ERP score & pitch using all accumulated signals."""
    tags = data.get("tags", [])
    coverage = data.get("coverage", EMPTY_COVERAGE)

    tag_str = ", ".join(tags) if isinstance(tags, list) else str(tags)
    coverage_summary = _build_coverage_summary(coverage)

    primary_bottleneck = coverage.get("pain_point", {}).get("value") or ""

    rag_context = ""
    if primary_bottleneck:
        try:
            from containers.implementation.utils.rag_helper import rag_retrieve
            chunks = await rag_retrieve(
                primary_bottleneck,
                "business_bottlenecks",
                top_k=2,
            )
            rag_context = "\n\n".join(chunks)
        except Exception as e:
            print(f"⚠️ RAG Retrieval failed for bottleneck: {e!r}")
            import os
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
        from llm_router import invoke_smart_llm
        response = await invoke_smart_llm([("human", formatted_prompt)])
        return _parse_llm_json(response.content)

    except Exception as e:
        print(f"❌ Recommendation Error: {e!r}")
        industry_val = coverage.get("industry", {}).get("value", "")
        is_mfg = "manufactur" in (industry_val or "").lower()
        return {
            "recommended_erp": "ERPNext Manufacturing (Standard)" if is_mfg else "ERPNext Distribution & Commerce",
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


@activity.defn
async def save_discovery_metadata(data: dict):
    """Final write — marks discovery COMPLETE and saves the recommendation."""
    pid = data.get("project_id")
    if isinstance(pid, str):
        pid = UUID(pid)

    rec = data.get("recommendation", {})
    coverage = data.get("coverage", None)

    async with engine.begin() as conn:
        await conn.execute(
            update(Hook)
            .where(Hook.project_id == pid)
            .values(
                discovery_status="COMPLETE",
                discovery_coverage=coverage,
                discovery_metadata={
                    "f3iche": rec.get("f3iche", "trading"),
                    "industry": rec.get("industry", ""),
                    "price_plan": rec.get("price_plan", "Standard"),
                    "recommended_erp": rec.get("recommended_erp"),
                    "fit_score": rec.get("fit_score"),
                    "mvp_focus": rec.get("mvp_focus"),
                },
            )
        )
    return True
