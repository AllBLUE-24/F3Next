import os
import json
import aiohttp
import asyncio
from pathlib import Path
from dotenv import load_dotenv

from containers.erpnext.config.knowledge_base import ERPNEXT_STOCK_KB_TEXT
from containers.erpnext.config.prompts import CONFIG_GENERATOR_PROMPT
from containers.erpnext.config.schema import TARGET_STRUCTURE_JSON

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(dotenv_path=ROOT_DIR / ".env")

async def generate_final_config_json(tags: list, answers: dict) -> dict:
    """
    Sends the gathered state to the Gemini REST API via the smart key router.
    Uses 'gemini-flash-latest' for maximum Free Tier stability.
    """
    from llm_router import invoke_smart_llm

    MODEL_NAME = "gemini-flash-latest"

    # Compile Context
    user_context = f"""
    TARGET JSON SCHEMA: {TARGET_STRUCTURE_JSON}
    USER DATA: Tags={json.dumps(tags)}, Answers={json.dumps(answers)}
    KNOWLEDGE BASE: {ERPNEXT_STOCK_KB_TEXT}
    """

    prompt = f"SYSTEM: {CONFIG_GENERATOR_PROMPT}\n\nUSER: {user_context}"
    
    print(f"📡 Connecting to Gemini ({MODEL_NAME}) via Router...")

    try:
        response = await invoke_smart_llm([("human", prompt)], model_name=MODEL_NAME, temperature=0.1)
        raw_text = response.content
        
        print("✅ AI Config Generated Successfully.")
        
        try:
            return json.loads(raw_text)
        except Exception as parse_err:
            clean_text = raw_text.replace('```json', '').replace('```', '').strip()
            try:
                return json.loads(clean_text)
            except:
                print(f"❌ Parsing Error: {parse_err}")
                return {"error": "Parsing failed", "details": str(parse_err)}
    except Exception as e:
        print(f"❌ Connection or Router Failed: {e}")
        return {"error": "Connection failed", "details": str(e)}