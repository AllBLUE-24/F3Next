import os
import json
from temporalio import activity
from containers.discovery.prompts import DISCOVERY_PROMPT, RECOMMENDATION_PROMPT
from containers.discovery.knowledge_base import KNOWLEDGE_BASE
from shared.database.db import engine
from shared.models.hooks import Hook
from sqlalchemy import update


async def _call_ollama(system: str, user: str) -> str:
    """Call Ollama API directly — uses native /api/chat endpoint."""
    import httpx
    base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
    # Default to small model (~1.3GB) so it runs on limited RAM; override with OLLAMA_MODEL
    model = os.getenv("OLLAMA_MODEL", "llama3.2:1b")
    if ":" not in model:
        model = f"{model}:latest"
    url = f"{base}/api/chat"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": False,
    }
    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.post(url, json=payload)
        if r.status_code != 200:
            body = r.text[:500] if r.text else "(empty)"
            print(f"Ollama error {r.status_code}: {body}")
            raise httpx.HTTPStatusError(
                f"Ollama returned {r.status_code}: {body}",
                request=r.request,
                response=r,
            )
        data = r.json()
    msg = data.get("message", {})
    content = msg.get("content") or msg.get("text")
    if not content:
        raise ValueError("Ollama returned empty content")
    return content


def _use_ollama() -> bool:
    """Check if Ollama should be used (default: yes when no Gemini key)."""
    return not os.getenv("GEMINI_API_KEY")


def _mock_discovery_response(user_answer: str, current_step: int) -> dict:
    """Fallback when Ollama is unavailable — progresses through steps with simple rules."""
    next_step = min(current_step + 1, 6)
    # Extract basic tags from answer
    tags = []
    ans_lower = (user_answer or "").lower()
    if any(w in ans_lower for w in ["manufacture", "factory", "produce", "make"]):
        tags.append("#Ind_Manufacturing")
    if any(w in ans_lower for w in ["trade", "sell", "distribute"]):
        tags.append("#Ind_Retail")
    if any(w in ans_lower for w in ["excel", "spreadsheet"]):
        tags.append("#Legacy_Excel")
    if any(w in ans_lower for w in ["tally"]):
        tags.append("#Legacy_Tally")
    if not tags:
        tags.append("#Ind_Manufacturing")
    questions = {
        1: "What does your company manufacture or trade?",
        2: "Do you make to stock, make to order, or do job work?",
        3: "What is your approximate annual turnover (in Cr)?",
        4: "What system do you use today — Excel, Tally, or an ERP?",
        5: "What is your biggest pain point — inventory, costing, or efficiency?",
    }
    next_q = questions.get(next_step, "Thank you! Generating your ERP recommendation...")
    return {
        "status": "SUCCESS",
        "reason": "mock",
        "extracted_tags": tags,
        "bot_response": f"Got it. {next_q}",
        "next_step_id": next_step,
        "f3iche_hint": "manufacturing" if "manufacture" in ans_lower else "trading",
        "industry_hint": "Manufacturing" if "manufacture" in ans_lower else "Trading",
    }

# Map step IDs to concepts
STEP_MAP = {
    1: {"concept": "Industry & Identity", "target": "#Ind_Manufacturing, #Ind_Process, #Ind_Discrete"},
    2: {"concept": "Fulfillment Strategy", "target": "#Strat_MTS, #Strat_MTO, #JobWork"},
    3: {"concept": "Scale & Validation", "target": "#Scale_SMB, #Users_Ratio"},
    4: {"concept": "Legacy Tech Stack", "target": "#Legacy_Excel, #Legacy_Tally"},
    5: {"concept": "Core Business Pain", "target": "#Goal_Inventory, #Goal_Efficiency"}
}

@activity.defn
async def analyze_discovery_turn(data: dict) -> dict:
    """Uses Ollama (local) or Gemini to validate, extract tags, and generate the next question."""
    user_answer = data.get("user_answer")
    current_step = data.get("current_step", 1)
    history = data.get("history", "")
    step_info = STEP_MAP.get(current_step, STEP_MAP[1])

    formatted_prompt = DISCOVERY_PROMPT.format(
        current_step=current_step,
        target_concept_for_this_step=step_info["concept"],
        user_answer=user_answer,
        next_step=current_step + 1
    )
    system_context = f"Use these validation rules: {json.dumps(KNOWLEDGE_BASE['validation_rules'])}"

    # Use mock when OLLAMA_FALLBACK=true (e.g. Ollama not working)
    if os.getenv("OLLAMA_FALLBACK", "").lower() in ("true", "1", "yes"):
        result = _mock_discovery_response(user_answer, current_step)
        result["message"] = result.get("bot_response")
        return result

    try:
        if _use_ollama():
            content = await _call_ollama(system_context, formatted_prompt)
        else:
            from langchain_google_genai import ChatGoogleGenerativeAI
            llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=os.getenv("GEMINI_API_KEY"))
            response = await llm.ainvoke([("system", system_context), ("human", formatted_prompt)])
            content = response.content

        clean_json = content.replace("```json", "").replace("```", "").strip()
        result = json.loads(clean_json)
        result["message"] = result.get("bot_response")
        return result

    except Exception as e:
        print(f"❌ AI Activity Error: {str(e)}")
        # Fallback to mock so Discovery flow continues when Ollama fails
        if os.getenv("OLLAMA_FALLBACK_ON_ERROR", "true").lower() in ("true", "1", "yes"):
            print("Using mock response (Ollama unavailable)")
            result = _mock_discovery_response(user_answer, current_step)
            result["message"] = result.get("bot_response")
            return result
        return {
            "status": "RETRY",
            "message": "I encountered a temporary connection issue. Could you please repeat that?",
            "bot_response": "I encountered a temporary connection issue. Could you please repeat that?",
            "reason": str(e),
            "next_step_id": current_step
        }

@activity.defn
async def save_discovery_state(data: dict):
    from uuid import UUID
    pid = data.get("project_id")
    if isinstance(pid, str):
        pid = UUID(pid)

    # Ensure we save the text to the DB correctly
    bot_text = data.get("message") or data.get("bot_response")

    async with engine.begin() as conn:
        await conn.execute(
            update(Hook)
            .where(Hook.project_id == pid) # Ensure this matches UUID in DB
            .values(
                last_bot_response=bot_text, # Saving the text here
                discovery_step=data.get("step"),
                extracted_tags=data.get("tags"),
                discovery_status="PROCESSING" if data.get("step") <= 5 else "COMPLETE"
            )
        )
    return True

def _mock_erp_recommendation(tags: list) -> dict:
    """Fallback when Ollama/Gemini unavailable."""
    return {
        "recommended_erp": "ERPNext Manufacturing (Standard)",
        "fit_score": 85,
        "headline": "A good match for your operations",
        "reasoning": "Based on your inputs, ERPNext is a strong candidate for your operations.",
        "f3iche": "manufacturing",
        "industry": "General",
        "price_plan": "Standard",
    }


@activity.defn
async def generate_erp_recommendation(tags: list) -> dict:
    """
    Final Step: Takes the collected tags and generates the ERP Score & Pitch.
    Uses Ollama (local) or Gemini. Falls back to mock on error so the activity
    completes within Temporal's timeout.
    """
    if os.getenv("OLLAMA_FALLBACK", "").lower() in ("true", "1", "yes"):
        return _mock_erp_recommendation(tags)

    tag_str = ", ".join(tags) if isinstance(tags, list) else str(tags)
    formatted_prompt = RECOMMENDATION_PROMPT.format(extracted_tags=tag_str)

    try:
        if _use_ollama():
            import asyncio
            # Short timeout so we don't hit Temporal's activity timeout (2 min)
            content = await asyncio.wait_for(_call_ollama("", formatted_prompt), timeout=45.0)
        else:
            from langchain_google_genai import ChatGoogleGenerativeAI
            llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=os.getenv("GEMINI_API_KEY"))
            response = await llm.ainvoke([("human", formatted_prompt)])
            content = response.content

        clean_json = content.replace("```json", "").replace("```", "").strip()
        recommendation = json.loads(clean_json)
        return recommendation

    except Exception as e:
        print(f"❌ Recommendation Error: {e!r}")
        return _mock_erp_recommendation(tags if isinstance(tags, list) else [])


@activity.defn
async def save_discovery_metadata(data: dict):
    """Save f3iche, industry, price_plan to Hook.discovery_metadata."""
    from uuid import UUID
    pid = data.get("project_id")
    if isinstance(pid, str):
        pid = UUID(pid)
    rec = data.get("recommendation", {})

    async with engine.begin() as conn:
        await conn.execute(
            update(Hook)
            .where(Hook.project_id == pid)
            .values(
                discovery_metadata={
                    "f3iche": rec.get("f3iche", "trading"),
                    "industry": rec.get("industry", ""),
                    "price_plan": rec.get("price_plan", "Standard"),
                    "recommended_erp": rec.get("recommended_erp"),
                    "fit_score": rec.get("fit_score"),
                }
            )
        )
    return True