import os
import json
from uuid import UUID
from temporalio import activity
from containers.discovery.prompts import DISCOVERY_PROMPT, RECOMMENDATION_PROMPT
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

# Friendly display labels for the coverage summary injected into prompts
_DIM_LABELS = {
    "industry":      "Industry & business type",
    "strategy":      "Fulfillment strategy",
    "scale":         "Business scale",
    "legacy_system": "Current software / system",
    "pain_point":    "Biggest operational challenge",
}

# ------------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------------

def _build_coverage_summary(coverage: dict) -> str:
    """
    Converts the coverage dict into a human-readable block for prompt injection.
    Example output:
        ✅ Industry:         Automotive Manufacturing (confirmed)
        ⏳ Strategy:         Mix of MTO and job work (partial)
        ❓ Scale:            Unknown
    """
    lines = []
    for dim, label in _DIM_LABELS.items():
        entry = coverage.get(dim, {"status": None, "value": None})
        status = entry.get("status")
        value  = entry.get("value") or "—"
        if status == "confirmed":
            icon = "✅"
        elif status == "partial":
            icon = "⏳"
        else:
            icon = "❓"
            value = "Unknown"
        lines.append(f"  {icon} {label:<32} {value}")
    return "\n".join(lines)


def _merge_coverage(existing: dict, updated: dict) -> dict:
    """
    Merges LLM-returned updated_coverage into existing coverage.
    Only overrides a dimension if the new status is non-null.
    'confirmed' always wins over 'partial'.
    """
    result = {dim: dict(entry) for dim, entry in existing.items()}

    for dim, new_entry in updated.items():
        if dim not in result:
            continue
        new_status = new_entry.get("status")
        new_value  = new_entry.get("value")

        old_status = result[dim].get("status")

        # Never downgrade confirmed → partial
        if old_status == "confirmed" and new_status == "partial":
            continue

        if new_status is not None:
            result[dim]["status"] = new_status
        if new_value is not None:
            result[dim]["value"] = new_value

    return result


def _coverage_is_complete(coverage: dict, turn: int) -> bool:
    """
    Discovery is considered complete when:
      - 4 or more dimensions have at least 'partial' status, OR
      - We've hit the max turn guardrail.
    """
    filled = sum(
        1 for v in coverage.values()
        if v.get("status") in ("partial", "confirmed")
    )
    return filled >= 4 or turn >= MAX_TURNS


def _smart_fallback_response(coverage: dict, turn: int, user_answer: str) -> dict:
    """
    Intelligent fallback when the LLM call fails.
    Instead of canned questions, picks the first uncovered dimension
    and asks about it naturally.
    """
    templates = KNOWLEDGE_BASE["clarification_templates"]
    dim_questions = {
        "industry":      templates["vague_industry"],
        "strategy":      templates["vague_strategy"],
        "scale":         templates["vague_scale"],
        "legacy_system": templates["vague_legacy"],
        "pain_point":    templates["vague_pain"],
    }

    # Find the first dimension that's still unknown
    for dim in ["industry", "strategy", "scale", "legacy_system", "pain_point"]:
        if coverage.get(dim, {}).get("status") is None:
            question = dim_questions[dim]
            return {
                "status":           "SUCCESS",
                "reason":           "llm_fallback",
                "answer_quality":   "vague",
                "extracted_tags":   [],
                "updated_coverage": coverage,
                "bot_response":     f"Got it. {question}",
                "is_complete":      _coverage_is_complete(coverage, turn + 1),
                "f3iche_hint":      None,
                "industry_hint":    None,
            }

    # All covered — wrap up
    return {
        "status":           "SUCCESS",
        "reason":           "llm_fallback_complete",
        "answer_quality":   "clear",
        "extracted_tags":   [],
        "updated_coverage": coverage,
        "bot_response":     "Thanks — I think I have a good picture of your business. Let me generate your ERP recommendation now.",
        "is_complete":      True,
        "f3iche_hint":      None,
        "industry_hint":    None,
    }


# ------------------------------------------------------------------
# ACTIVITIES
# ------------------------------------------------------------------

@activity.defn
async def analyze_discovery_turn(data: dict) -> dict:
    """
    Core intelligence activity. Calls the LLM with full coverage state
    and returns an updated coverage object + Adi's next message.
    """
    user_answer         = data.get("user_answer", "")
    current_coverage    = data.get("current_coverage", EMPTY_COVERAGE)
    accumulated_tags    = data.get("accumulated_tags", [])
    conversation_history = data.get("conversation_history", [])
    turn_count          = data.get("turn_count", 0)

    coverage_summary    = _build_coverage_summary(current_coverage)
    history_text        = "\n".join(conversation_history[-12:]) if conversation_history else "(none yet)"

    formatted_prompt = DISCOVERY_PROMPT.format(
        coverage_summary=coverage_summary,
        conversation_history=history_text,
        user_answer=user_answer,
        accumulated_tags=", ".join(accumulated_tags) if accumulated_tags else "none yet",
    )

    system_context = (
        "You are Adi, an ERP consultant. Follow the instructions exactly. "
        f"Validation rules: {json.dumps(KNOWLEDGE_BASE['validation_rules'])}. "
        f"Signal vocabulary summary: industry keywords include manufacturing, retail, service, trading. "
        "Return ONLY valid JSON."
    )

    try:
        from llm_router import invoke_smart_llm
        response = await invoke_smart_llm([
            ("system", system_context),
            ("human",  formatted_prompt),
        ])
        content = response.content

        # Robust JSON extraction
        start_idx = content.find('{')
        end_idx   = content.rfind('}')
        if start_idx != -1 and end_idx != -1:
            clean_json = content[start_idx:end_idx + 1]
        else:
            clean_json = content.replace("```json", "").replace("```", "").strip()

        result = json.loads(clean_json)

        # Merge coverage (don't trust LLM to give us the full object, just diffs)
        llm_updated = result.get("updated_coverage", {})
        merged_coverage = _merge_coverage(current_coverage, llm_updated)

        # Safety: ensure is_complete logic is consistent
        result["updated_coverage"] = merged_coverage
        result["message"] = result.get("bot_response", "")

        # Override is_complete using our own completeness logic if LLM missed it
        if _coverage_is_complete(merged_coverage, turn_count + 1):
            result["is_complete"] = True

        return result

    except Exception as e:
        print(f"❌ Adi Activity Error (turn {turn_count}): {str(e)}")
        fallback = _smart_fallback_response(current_coverage, turn_count, user_answer)
        fallback["message"] = fallback.get("bot_response", "")
        return fallback


@activity.defn
async def save_discovery_state(data: dict):
    """
    Persists the current conversation state to the hooks table after each turn.
    Now writes coverage + turn_count in addition to the original fields.
    """
    pid = data.get("project_id")
    if isinstance(pid, str):
        pid = UUID(pid)

    bot_text     = data.get("message") or data.get("bot_response", "")
    coverage     = data.get("coverage")
    turn_count   = data.get("turn_count", 0)
    current_step = data.get("step", 1)        # kept for any UI still reading this
    tags         = data.get("tags", [])

    is_complete = data.get("is_complete", False)

    async with engine.begin() as conn:
        await conn.execute(
            update(Hook)
            .where(Hook.project_id == pid)
            .values(
                last_bot_response   = bot_text,
                discovery_step      = current_step,
                extracted_tags      = tags,
                discovery_coverage  = coverage,
                discovery_turn_count= turn_count,
                discovery_status    = "COMPLETE" if is_complete else "PROCESSING",
            )
        )
    return True


@activity.defn
async def generate_erp_recommendation(data: dict) -> dict:
    """
    Final step: generate the ERP score & pitch using all accumulated signals.
    Now receives both tags AND the coverage summary for richer context.
    """
    tags     = data.get("tags", [])
    coverage = data.get("coverage", EMPTY_COVERAGE)

    tag_str          = ", ".join(tags) if isinstance(tags, list) else str(tags)
    coverage_summary = _build_coverage_summary(coverage)

    formatted_prompt = RECOMMENDATION_PROMPT.format(
        extracted_tags  = tag_str,
        coverage_summary= coverage_summary,
    )

    try:
        from llm_router import invoke_smart_llm
        response = await invoke_smart_llm([("human", formatted_prompt)])
        content  = response.content

        start_idx = content.find('{')
        end_idx   = content.rfind('}')
        if start_idx != -1 and end_idx != -1:
            clean_json = content[start_idx:end_idx + 1]
        else:
            clean_json = content.replace("```json", "").replace("```", "").strip()

        return json.loads(clean_json)

    except Exception as e:
        print(f"❌ Recommendation Error: {e!r}")
        # Fallback recommendation based on coverage
        industry_val = coverage.get("industry", {}).get("value", "")
        is_mfg = "manufactur" in (industry_val or "").lower()
        return {
            "recommended_erp": "ERPNext Manufacturing (Standard)" if is_mfg else "ERPNext Distribution & Commerce",
            "fit_score":        78,
            "headline":         "Strong Match for Your Business Profile",
            "reasoning":        "Based on your profile, ERPNext covers your core operational needs out of the box. We can tailor the configuration to your specific pain points.",
            "f3iche":           "manufacturing" if is_mfg else "trading",
            "industry":         industry_val or "General",
            "price_plan":       "Standard",
        }


@activity.defn
async def save_discovery_metadata(data: dict):
    """
    Final write — marks discovery COMPLETE and saves the recommendation.
    """
    pid = data.get("project_id")
    if isinstance(pid, str):
        pid = UUID(pid)

    rec      = data.get("recommendation", {})
    coverage = data.get("coverage", None)

    async with engine.begin() as conn:
        await conn.execute(
            update(Hook)
            .where(Hook.project_id == pid)
            .values(
                discovery_status   = "COMPLETE",
                discovery_coverage = coverage,   # persist final coverage too
                discovery_metadata = {
                    "f3iche":           rec.get("f3iche", "trading"),
                    "industry":         rec.get("industry", ""),
                    "price_plan":       rec.get("price_plan", "Standard"),
                    "recommended_erp":  rec.get("recommended_erp"),
                    "fit_score":        rec.get("fit_score"),
                }
            )
        )
    return True