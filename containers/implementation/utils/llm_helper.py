from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Dict, Any

# Ensure we can import from root llm_router
project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from llm_router import invoke_smart_llm_sync

logger = logging.getLogger(__name__)


def generate_json(prompt: str, model_name: str = "gemini-2.5-flash", **kwargs) -> Dict[str, Any]:
    """
    Sends a prompt to Gemini using the root llm_router and enforces JSON output.
    Returns the parsed Python dictionary.
    """
    logger.info(f"Generating content using {model_name} via llm_router...")
    
    prompt_with_instructions = prompt + "\n\nCRITICAL: Output ONLY valid JSON. Your entire response MUST evaluate correctly with JSON.parse(). Do not wrap in ```json block."
    
    response = invoke_smart_llm_sync([("user", prompt_with_instructions)], model_name=model_name, **kwargs)
    
    text = response.content if hasattr(response, 'content') else str(response)
    if not text:
        raise ValueError("Received empty response from Gemini via llm_router.")
        
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        cleaned = text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
            
        try:
            return json.loads(cleaned.strip())
        except Exception:
            logger.error(f"Failed to parse fallback JSON from Gemini. Raw text:\n {text}")
            raise ValueError("Failed to parse JSON from Gemini response.")
