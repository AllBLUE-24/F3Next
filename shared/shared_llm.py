"""
shared_llm.py  —  Universal JSON-mode LLM Helper
=================================================
Wraps llm_router with Gemini's native JSON response mode, automatic token
escalation on truncation, and markdown-fence stripping.

Available to ALL containers (os/, discovery/, implementation/, etc.).

Usage:
    from shared_llm import generate_json

    result: dict = generate_json(
        prompt="...",
        model_name="gpt-4o-mini",   # optional — defaults to primary tier
        max_output_tokens=4000,           # optional
        temperature=0.1,                  # optional
    )
"""

from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict

# Ensure root is on sys.path when imported from a sub-container
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from llm_router import invoke_smart_llm_sync  # noqa: E402

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _clean_json_text(text: str) -> str:
    """Strip markdown fences and surrounding whitespace from an LLM response."""
    cleaned = text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    return cleaned.strip()


def _is_truncated_json(text: str) -> bool:
    """Return True if the JSON appears to be cut off mid-response."""
    text = text.strip()
    if not text:
        return True
    open_braces = text.count("{") - text.count("}")
    open_brackets = text.count("[") - text.count("]")
    return open_braces > 0 or open_brackets > 0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_json(
    prompt: str,
    model_name: str = "gpt-4o-mini",
    **kwargs,
) -> Dict[str, Any]:
    """
    Send a prompt to Gemini via llm_router and return a parsed Python dict.

    - Uses Gemini's native JSON mode (response_mime_type="application/json")
      for reliable, fence-free JSON output.
    - On a truncated response, escalates max_output_tokens and retries
      (up to 3 attempts: base → 2× → 4×).
    - Model/key switching is handled transparently by llm_router; this
      function just retries on *truncation*, not on quota errors.

    Args:
        prompt:            The user/system prompt to send.
        model_name:        Gemini model to start with (falls back via tiers).
        **kwargs:          Forwarded to invoke_smart_llm_sync.
                           Notable keys: temperature, max_output_tokens.

    Returns:
        Parsed dict from the LLM response.

    Raises:
        ValueError: If JSON cannot be parsed after 3 attempts.
    """
    base_tokens = kwargs.pop("max_output_tokens", 4000)
    token_steps = [base_tokens, base_tokens * 2, base_tokens * 4]

    last_error: Exception | None = None
    last_raw = ""

    for attempt, max_tokens in enumerate(token_steps, start=1):
        logger.info(
            "[shared_llm] generate_json attempt %d/%d | model=%s | max_output_tokens=%d",
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

            text = response.content if hasattr(response, "content") else str(response)
            last_raw = text

            if not text:
                last_error = ValueError("Empty response from LLM.")
                logger.warning("[shared_llm] Attempt %d: empty response — retrying", attempt)
                time.sleep(attempt)
                continue

            # Try the raw text first (JSON mode usually returns clean JSON)
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                pass

            # Strip possible markdown fences and retry parse
            cleaned = _clean_json_text(text)
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError:
                pass

            # If truncated, retry with more tokens
            if _is_truncated_json(cleaned):
                logger.warning(
                    "[shared_llm] Attempt %d: JSON truncated (unbalanced braces) — "
                    "retrying with more tokens",
                    attempt,
                )
                last_error = ValueError(f"Truncated JSON on attempt {attempt}")
                time.sleep(attempt)
                continue

            # Not truncated but invalid — more tokens won't help
            logger.error("[shared_llm] Attempt %d: malformed (non-truncated) JSON.", attempt)
            last_error = ValueError("Malformed JSON from LLM.")
            break

        except Exception as exc:
            last_error = exc
            logger.warning("[shared_llm] Attempt %d failed: %s", attempt, exc)
            time.sleep(attempt)
            continue

    logger.error(
        "[shared_llm] generate_json failed after %d attempts. Last raw (truncated):\n%s",
        len(token_steps), last_raw[:2000],
    )
    raise ValueError(
        f"[shared_llm] Failed to parse JSON after {len(token_steps)} attempts: {last_error}"
    )
