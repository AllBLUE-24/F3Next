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
    Sends the gathered state to the Gemini REST API via aiohttp.
    Uses 'gemini-flash-latest' for maximum Free Tier stability.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return {"error": "Missing GEMINI_API_KEY"}

    # 🔴 FIX: Use the generic alias. 
    # This maps to the stable 1.5 Flash (15 RPM) instead of the restricted 2.0 Preview.
    MODEL_NAME = "gemini-flash-latest" 

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={api_key}"
    
    # Compile Context
    user_context = f"""
    TARGET JSON SCHEMA: {TARGET_STRUCTURE_JSON}
    USER DATA: Tags={json.dumps(tags)}, Answers={json.dumps(answers)}
    KNOWLEDGE BASE: {ERPNEXT_STOCK_KB_TEXT}
    """

    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{
            "parts": [{"text": f"SYSTEM: {CONFIG_GENERATOR_PROMPT}\n\nUSER: {user_context}"}]
        }],
        "generationConfig": {
            "response_mime_type": "application/json",
            "temperature": 0.1
        }
    }

    print(f"📡 Connecting to Gemini ({MODEL_NAME})...")

    # Retry Logic (Increased wait time just in case)
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as resp:
                    
                    # HANDLE RATE LIMITS (429)
                    if resp.status == 429:
                        wait_time = 15 * (attempt + 1) # Increased wait to 15s, 30s, 45s
                        print(f"⚠️ Rate Limit Hit (429). Waiting {wait_time}s before retry {attempt + 1}/{max_retries}...")
                        await asyncio.sleep(wait_time)
                        continue 

                    # HANDLE OTHER ERRORS
                    if resp.status != 200:
                        text = await resp.text()
                        print(f"❌ Gemini Error {resp.status}: {text}")
                        return {"error": f"HTTP {resp.status}", "details": text}
                    
                    # SUCCESS
                    result = await resp.json()
                    try:
                        raw_text = result['candidates'][0]['content']['parts'][0]['text']
                        print("✅ AI Config Generated Successfully.")
                        return json.loads(raw_text)
                    except Exception as parse_err:
                        # Fallback for when Gemini wraps JSON in markdown blocks
                        clean_text = raw_text.replace('```json', '').replace('```', '').strip()
                        try:
                            return json.loads(clean_text)
                        except:
                            print(f"❌ Parsing Error: {parse_err}")
                            return {"error": "Parsing failed", "details": str(parse_err)}

        except Exception as e:
            print(f"❌ Connection Failed: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(5)
            else:
                return {"error": "Connection failed", "details": str(e)}

    return {"error": "Max retries exceeded"}