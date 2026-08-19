"""Marketing consultant chat — stateless LLM replies for anonymous website leads."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from containers.marketing.prompts import CONSULTANT_SYSTEM_PROMPT, OPENING_MESSAGE

logger = logging.getLogger(__name__)

MARKETING_CHAT_MODEL = os.getenv("MARKETING_CHAT_MODEL", "gpt-4o-mini")
CHAT_TEMPERATURE = float(os.getenv("MARKETING_CHAT_TEMPERATURE", "0.75"))
MAX_OUTPUT_TOKENS = int(os.getenv("MARKETING_CHAT_MAX_TOKENS", "500"))
MIN_TURNS_BEFORE_SOLUTION = int(os.getenv("MARKETING_MIN_TURNS_BEFORE_SOLUTION", "3"))


def opening_message() -> str:
    return OPENING_MESSAGE


def _parse_llm_json(content: str) -> dict[str, Any]:
    start_idx = content.find("{")
    end_idx = content.rfind("}")
    if start_idx != -1 and end_idx != -1:
        clean_json = content[start_idx : end_idx + 1]
    else:
        clean_json = content.replace("```json", "").replace("```", "").strip()
    return json.loads(clean_json)


def _to_langchain_messages(
    history: list[dict[str, str]],
    *,
    user_turns: int,
) -> list[tuple[str, str]]:
    phase_hint = ""
    if user_turns >= MIN_TURNS_BEFORE_SOLUTION:
        phase_hint = (
            f"\n\nCONTEXT: The lead has sent {user_turns} messages. "
            "If you understand their bottleneck well enough, move to the solution overview "
            "and set show_contact to true. Otherwise ask one more sharp clarifying question."
        )

    lc: list[tuple[str, str]] = [("system", CONSULTANT_SYSTEM_PROMPT + phase_hint)]
    for msg in history:
        role = msg.get("role")
        content = (msg.get("content") or "").strip()
        if not content:
            continue
        if role == "user":
            lc.append(("human", content))
        elif role == "assistant":
            lc.append(("ai", content))
    return lc


async def generate_consultant_reply(
    history: list[dict[str, str]],
    *,
    user_message: str,
) -> dict[str, Any]:
    """Return { reply, show_contact } from the consultant model."""
    from llm_router import invoke_smart_llm

    user_turns = sum(1 for m in history if m.get("role") == "user") + 1
    messages = [*history, {"role": "user", "content": user_message}]
    lc_messages = _to_langchain_messages(history, user_turns=user_turns)
    lc_messages.append(("human", user_message))

    try:
        response = await invoke_smart_llm(
            lc_messages,
            model_name=MARKETING_CHAT_MODEL,
            temperature=CHAT_TEMPERATURE,
            max_output_tokens=MAX_OUTPUT_TOKENS,
            response_mime_type="application/json",
        )
        raw = _parse_llm_json(response.content or "")
        reply = (raw.get("reply") or "").strip()
        show_contact = bool(raw.get("show_contact"))
        if not reply:
            raise ValueError("Empty reply from consultant model")
        return {"reply": reply, "show_contact": show_contact, "user_turns": user_turns}
    except Exception as e:
        logger.error("Marketing chat LLM failed: %r", e)
        return {
            "reply": (
                "I'm having a brief connection hiccup — but I'd still love to hear more. "
                "What's the one thing that eats most of your team's time every week?"
            ),
            "show_contact": False,
            "user_turns": user_turns,
        }
