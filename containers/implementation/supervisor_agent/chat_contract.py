"""
Supervisor chat contract — single policy for when chat must signal the workflow.

Blocking prompts (validation, data_readiness) halt Temporal until supervisor_response.
Non-blocking prompts (mapping) are informational only.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

# Steps where an open ask_user prompt blocks the Temporal workflow.
BLOCKING_SUPERVISOR_STEPS = frozenset({"validation", "data_readiness"})


def is_blocking_supervisor_prompt(prompt: Dict[str, Any]) -> bool:
    """True when this prompt must receive supervisor_response before the pipeline continues."""
    step = str(prompt.get("step") or "")
    if step not in BLOCKING_SUPERVISOR_STEPS:
        return False
    actions = prompt.get("actions") or []
    return any(isinstance(a, dict) and a.get("type") == "ask_user" for a in actions)


def open_blocking_prompts(context: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Open supervisor prompts that currently block the workflow."""
    return [
        p
        for p in (context.get("open_supervisor_prompts") or [])
        if isinstance(p, dict) and is_blocking_supervisor_prompt(p)
    ]


def chat_must_signal_supervisor(context: Dict[str, Any]) -> bool:
    """Any chat reply while a blocking prompt is open must signal the workflow."""
    return bool(open_blocking_prompts(context))


def primary_ask_action(prompt: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    actions = prompt.get("actions") or []
    for action in actions:
        if isinstance(action, dict) and action.get("type") == "ask_user":
            return action
    return None


def build_supervisor_extra_data(
    message: str,
    prompt: Dict[str, Any],
    *,
    upload_intent: bool = False,
) -> Dict[str, Any]:
    """Normalize chat/upload payloads for supervisor_response signals."""
    action = primary_ask_action(prompt) or {}
    options = [str(o) for o in (action.get("options") or []) if o]
    extra: Dict[str, Any] = {"user_note": message.strip()}

    if upload_intent:
        upload_opt = next((o for o in options if "upload" in o.lower()), None)
        extra["selected_option"] = upload_opt or "Upload the missing files"
        extra["upload_intent"] = True
        return extra

    msg_lower = message.strip().lower()
    for opt in options:
        if msg_lower == opt.strip().lower() or msg_lower in opt.strip().lower():
            extra["selected_option"] = opt
            return extra

    if any(w in msg_lower for w in ("continue", "proceed", "yes", "skip", "confirm", "default")):
        for opt in options:
            if "continue" in opt.lower() or "default" in opt.lower() or "anyway" in opt.lower():
                extra["selected_option"] = opt
                return extra

    # Free-text resolution — workflow applies user_note via auto_fix.
    extra["apply_user_note"] = True
    meta = action.get("metadata") if isinstance(action.get("metadata"), dict) else {}
    if meta.get("sample_gaps"):
        extra["sample_gaps"] = meta.get("sample_gaps")
    return extra
