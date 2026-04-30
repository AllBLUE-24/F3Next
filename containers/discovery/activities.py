import os
import json
from uuid import UUID
from temporalio import activity
from langchain_google_genai import ChatGoogleGenerativeAI
from containers.discovery.prompts import DISCOVERY_PROMPT, RECOMMENDATION_PROMPT
from containers.discovery.knowledge_base import KNOWLEDGE_BASE
from shared.database.db import engine
from shared.models.hooks import Hook
from sqlalchemy import update

# Intentionally not establishing a single get_llm so we rely on the router

def _mock_discovery_response(user_answer: str, current_step: int) -> dict:
    """Fallback when API limits or network issues occur."""
    next_step = min(current_step + 1, 6)
    ans_lower = (user_answer or "").lower()
    tags = ["#Ind_Manufacturing"] if "manufacture" in ans_lower else ["#Ind_Retail"]
    
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
        "reason": "fallback",
        "extracted_tags": tags,
        "bot_response": f"Got it. {next_q}",
        "next_step_id": next_step
    }

STEP_MAP = {
    1: {"concept": "Industry & Identity"},
    2: {"concept": "Fulfillment Strategy"},
    3: {"concept": "Scale & Validation"},
    4: {"concept": "Legacy Tech Stack"},
    5: {"concept": "Core Business Pain"}
}

@activity.defn
async def analyze_discovery_turn(data: dict) -> dict:
    user_answer = data.get("user_answer")
    current_step = data.get("current_step", 1)
    previous_question = data.get("previous_question", "")
    accumulated_tags = data.get("accumulated_tags", []) # Pass from workflow
    
    step_info = STEP_MAP.get(current_step, STEP_MAP[1])
    
    formatted_prompt = DISCOVERY_PROMPT.format(
        current_step=current_step,
        target_concept_for_this_step=step_info["concept"],
        user_answer=user_answer,
        next_step=current_step + 1,
        previous_bot_question=previous_question,
        accumulated_tags=", ".join(accumulated_tags)
    )
    system_context = f"Use these validation rules: {json.dumps(KNOWLEDGE_BASE['validation_rules'])}"

    try:
        from llm_router import invoke_smart_llm
        response = await invoke_smart_llm([("system", system_context), ("human", formatted_prompt)])
        content = response.content

        start_idx = content.find('{')
        end_idx = content.rfind('}')
        if start_idx != -1 and end_idx != -1:
            clean_json = content[start_idx:end_idx+1]
        else:
            clean_json = content.replace("```json", "").replace("```", "").strip()

        result = json.loads(clean_json)
        result["message"] = result.get("bot_response")
        return result

    except Exception as e:
        print(f"❌ Gemini Activity Error: {str(e)}")
        # Graceful fallback to keep the user in the loop
        result = _mock_discovery_response(user_answer, current_step)
        result["message"] = result.get("bot_response")
        return result

@activity.defn
async def save_discovery_state(data: dict):
    pid = data.get("project_id")
    if isinstance(pid, str): pid = UUID(pid)

    bot_text = data.get("message") or data.get("bot_response")

    async with engine.begin() as conn:
        await conn.execute(
            update(Hook)
            .where(Hook.project_id == pid)
            .values(
                last_bot_response=bot_text,
                discovery_step=data.get("step"),
                extracted_tags=data.get("tags"),
                discovery_status="PROCESSING" if data.get("step") <= 5 else "COMPLETE"
            )
        )
    return True

@activity.defn
async def generate_erp_recommendation(tags: list) -> dict:
    """Final Step: Generates the ERP Score & Pitch using Gemini."""
    tag_str = ", ".join(tags) if isinstance(tags, list) else str(tags)
    formatted_prompt = RECOMMENDATION_PROMPT.format(extracted_tags=tag_str)

    try:
        from llm_router import invoke_smart_llm
        response = await invoke_smart_llm([("human", formatted_prompt)])
        content = response.content
        start_idx = content.find('{')
        end_idx = content.rfind('}')
        if start_idx != -1 and end_idx != -1:
            clean_json = content[start_idx:end_idx+1]
        else:
            clean_json = content.replace("```json", "").replace("```", "").strip()
            
        return json.loads(clean_json)

    except Exception as e:
        print(f"❌ Recommendation Error: {e!r}")
        return {
            "recommended_erp": "ERPNext Manufacturing",
            "fit_score": 80,
            "headline": "Standard Recommendation",
            "reasoning": "We encountered an issue generating a custom report, but based on your tags, ERPNext is highly suitable."
        }

@activity.defn
async def save_discovery_metadata(data: dict):
    pid = data.get("project_id")
    if isinstance(pid, str): pid = UUID(pid)
    rec = data.get("recommendation", {})

    async with engine.begin() as conn:
        await conn.execute(
            update(Hook)
            .where(Hook.project_id == pid)
            .values(
                discovery_status="COMPLETE", # <-- THIS IS THE CRITICAL FIX
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