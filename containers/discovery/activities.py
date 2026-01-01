import os
import json
from temporalio import activity
from langchain_google_genai import ChatGoogleGenerativeAI
from containers.discovery.prompts import DISCOVERY_PROMPT
from containers.discovery.knowledge_base import KNOWLEDGE_BASE
from shared.database.db import engine #
from shared.models.hooks import Hook #
from sqlalchemy import update

# Map step IDs to concepts for the prompt
STEP_MAP = {
    1: {"concept": "Industry & Identity", "target": "#Ind_Manufacturing, #Ind_Process, #Ind_Discrete"},
    2: {"concept": "Fulfillment Strategy", "target": "#Strat_MTS, #Strat_MTO, #JobWork"},
    3: {"concept": "Scale & Validation", "target": "#Scale_SMB, #Users_Ratio"},
    4: {"concept": "Legacy Tech Stack", "target": "#Legacy_Excel, #Legacy_Tally"},
    5: {"concept": "Core Business Pain", "target": "#Goal_Inventory, #Goal_Efficiency"}
}

@activity.defn
async def analyze_discovery_turn(data: dict) -> dict:
    """Uses Gemini to validate, extract tags, and generate the next question."""
    
    # 1. Setup Input
    user_answer = data.get("user_answer")
    current_step = data.get("current_step", 1)
    # Important: history prevents the LLM from repeating itself
    history = data.get("history", "") 
    
    step_info = STEP_MAP.get(current_step, STEP_MAP[1])
    
    # 2. Initialize Gemini
    api_key = os.getenv("GEMINI_API_KEY")
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=api_key)

    # 3. Format the Prompt
    formatted_prompt = DISCOVERY_PROMPT.format(
        current_step=current_step,
        target_concept_for_this_step=step_info["concept"],
        user_answer=user_answer,
        next_step=current_step + 1
    )
    
    # Optional: Inject Knowledge Base context into the prompt system message
    system_context = f"Use these validation rules: {json.dumps(KNOWLEDGE_BASE['validation_rules'])}"
    
    # 4. Invoke LLM
    response = await llm.ainvoke([
        ("system", system_context),
        ("human", formatted_prompt)
    ])

    # 5. Parse and Return JSON
    try:
        # Clean JSON in case LLM adds markdown triple backticks
        clean_json = response.content.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_json)
    except Exception as e:
        return {
            "status": "RETRY",
            "bot_response": "I didn't quite catch that. Could you tell me more about your factory setup?",
            "reason": f"JSON Parsing Error: {str(e)}"
        }

@activity.defn
async def save_discovery_state(data: dict):
    """Bridges the Agent container to the Postgres 'Hooks' table."""
    pid = data.get("project_id")
    
    async with engine.begin() as conn:
        await conn.execute(
            update(Hook)
            .where(Hook.project_id == pid)
            .values(
                last_bot_response=data.get("bot_response"),
                discovery_step=data.get("step"),
                extracted_tags=data.get("tags"),
                discovery_status="PROCESSING" if data.get("step") <= 5 else "COMPLETE"
            )
        )
    return True