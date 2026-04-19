from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path
from typing import Dict, Any

# Ensure we can import from root llm_router
project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from llm_router import invoke_smart_llm_sync

logger = logging.getLogger(__name__)


def _clean_json_text(text: str) -> str:
    """Strip markdown fences and whitespace from LLM response."""
    cleaned = text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    if cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    return cleaned.strip()


def _is_truncated_json(text: str) -> bool:
    """Detect if JSON was truncated mid-response (common with Gemini)."""
    text = text.strip()
    if not text:
        return True
    # Count braces/brackets — if unbalanced, likely truncated
    open_braces = text.count("{") - text.count("}")
    open_brackets = text.count("[") - text.count("]")
    return open_braces > 0 or open_brackets > 0


def generate_json(prompt: str, model_name: str = "gemini-2.5-flash", **kwargs) -> Dict[str, Any]:
    """
    Sends a prompt to Gemini using the root llm_router and enforces JSON output.
    Uses Gemini's native JSON mode via response_mime_type for reliable parsing.
    
    Retries up to 3 times with increasing max_output_tokens if JSON is truncated.
    Returns the parsed Python dictionary.
    """
    # Token escalation strategy: start with caller's value, escalate on truncation
    base_tokens = kwargs.pop("max_output_tokens", 4000)
    token_steps = [base_tokens, base_tokens * 2, base_tokens * 4]
    
    last_error = None
    last_raw_text = ""
    
    for attempt, max_tokens in enumerate(token_steps, 1):
        logger.info(
            "Generating JSON (attempt %d/%d) using %s | max_output_tokens=%d",
            attempt, len(token_steps), model_name, max_tokens,
        )
        
        try:
            response = invoke_smart_llm_sync(
                [("user", prompt)],
                model_name=model_name,
                response_mime_type="application/json",
                max_output_tokens=max_tokens,
                **kwargs,
            )
            
            text = response.content if hasattr(response, 'content') else str(response)
            last_raw_text = text
            
            if not text:
                last_error = ValueError("Received empty response from Gemini via llm_router.")
                logger.warning("  Attempt %d: empty response, retrying...", attempt)
                time.sleep(1 * attempt)
                continue
            
            # Try parsing directly first
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                pass
            
            # Try after cleaning markdown fences
            cleaned = _clean_json_text(text)
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError:
                pass
            
            # Check if truncated — if so, retry with more tokens
            if _is_truncated_json(cleaned):
                logger.warning(
                    "  Attempt %d: JSON appears truncated (unbalanced braces/brackets). "
                    "Retrying with higher max_output_tokens...",
                    attempt,
                )
                last_error = ValueError(f"Truncated JSON on attempt {attempt}")
                time.sleep(1 * attempt)
                continue
            
            # Not truncated but still invalid — unlikely to fix with more tokens
            logger.error("Attempt %d: JSON is not truncated but still invalid.", attempt)
            last_error = ValueError("Malformed (non-truncated) JSON from Gemini.")
            break
            
        except Exception as e:
            last_error = e
            logger.warning("  Attempt %d failed with error: %s", attempt, e)
            time.sleep(1 * attempt)
            continue
    
    # All attempts exhausted
    logger.error("Failed to parse JSON after %d attempts. Last raw text:\n%s", len(token_steps), last_raw_text[:2000])
    raise ValueError(f"Failed to parse JSON from Gemini after {len(token_steps)} attempts: {last_error}")
