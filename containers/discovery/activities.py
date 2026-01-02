import os
import json
from temporalio import activity
from langchain_google_genai import ChatGoogleGenerativeAI
from containers.discovery.prompts import DISCOVERY_PROMPT
from containers.discovery.knowledge_base import KNOWLEDGE_BASE
from shared.database.db import engine
from shared.models.hooks import Hook
from sqlalchemy import update

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
    """Uses Gemini to validate, extract tags, and generate the next question."""
    user_answer = data.get("user_answer")
    current_step = data.get("current_step", 1)
    history = data.get("history", "") 
    step_info = STEP_MAP.get(current_step, STEP_MAP[1])
    
    api_key = os.getenv("GEMINI_API_KEY")
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=api_key)

    formatted_prompt = DISCOVERY_PROMPT.format(
        current_step=current_step,
        target_concept_for_this_step=step_info["concept"],
        user_answer=user_answer,
        next_step=current_step + 1
    )
    
    system_context = f"Use these validation rules: {json.dumps(KNOWLEDGE_BASE['validation_rules'])}"
    
    try:
        # 1. Invoke LLM (Added Try/Except here to prevent Workflow crashes)
        response = await llm.ainvoke([
            ("system", system_context),
            ("human", formatted_prompt)
        ])
        
        # 2. Parse JSON
        clean_json = response.content.replace("```json", "").replace("```", "").strip()
        result = json.loads(clean_json)
        
        # 3. Standardization: Ensure we return 'message' not just 'bot_response'
        # This helps downstream mapping
        result["message"] = result.get("bot_response") 
        return result

    except Exception as e:
        print(f"❌ AI Activity Error: {str(e)}")
        return {
            "status": "RETRY",
            "message": "I encountered a temporary connection issue. Could you please repeat that?",
            "bot_response": "I encountered a temporary connection issue. Could you please repeat that?",
            "reason": str(e),
            "next_step_id": current_step
        }

@activity.defn
async def save_discovery_state(data: dict):
    pid = data.get("project_id")
    
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