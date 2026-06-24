"""
File IO — persist_supervisor_prompt activity.

Writes exception-driven Supervisor prompts to `is_supervisor_prompts` so the UI
can render them in a right-side conversation panel.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from temporalio import activity


@dataclass
class PersistSupervisorPromptInput:
    session_id: str
    step: str
    status: str = "open"  # open | answered | obsolete
    node_status: Optional[Dict[str, Any]] = None
    actions: List[Dict[str, Any]] = field(default_factory=list)
    summary_for_ui: str = ""
    answer_payload: Optional[Dict[str, Any]] = None


@activity.defn(name="persist_supervisor_prompt")
async def persist_supervisor_prompt(inp: PersistSupervisorPromptInput) -> str:
    from shared.database.db import AsyncSessionLocal
    from shared.models.is_models import ISSupervisorPrompt

    prompt_id = uuid.uuid4()
    try:
        async with AsyncSessionLocal() as session:
            session.add(
                ISSupervisorPrompt(
                    id=prompt_id,
                    session_id=uuid.UUID(inp.session_id),
                    step=inp.step,
                    status=inp.status,
                    node_status=inp.node_status,
                    actions=inp.actions,
                    summary_for_ui=inp.summary_for_ui,
                    answer_payload=inp.answer_payload,
                )
            )
            await session.commit()
    except Exception as e:
        activity.logger.error("  ❌ persist_supervisor_prompt failed: %s", e)
        return "error"

    if inp.status == "open" and inp.actions:
        try:
            from containers.implementation.file_io.persist_chat_message import save_chat_message
            from shared.quality_gate.chat_bridge import step_to_chat_step

                ask_actions = [a for a in inp.actions if isinstance(a, dict) and a.get("type") == "ask_user"]
            if ask_actions:
                questions = [a.get("question") for a in ask_actions if a.get("question")]
                user_facing = (questions[0] if questions else "").strip()
                if not user_facing:
                    user_facing = (inp.summary_for_ui or "").strip()
                if user_facing and not user_facing.startswith(f"{inp.step}:"):
                    chat_step = step_to_chat_step(inp.step, "IS")
                    if inp.step in ("upload", "analyze", "validate", "import"):
                        chat_step = inp.step
                    await save_chat_message(
                        inp.session_id,
                        chat_step,
                        "assistant",
                        user_facing,
                        message_type="supervisor_question",
                        message_metadata={
                            "supervisor_prompt_id": str(prompt_id),
                            "step": inp.step,
                            "actions": inp.actions,
                        },
                    )
        except Exception as e:
            activity.logger.warning("  ⚠ Could not mirror supervisor prompt to chat: %s", e)

    return str(prompt_id)


@dataclass
class MarkSupervisorPromptAnsweredInput:
    prompt_id: str
    answer_payload: Dict[str, Any] = field(default_factory=dict)
    status: str = "answered"


@dataclass
class ObsoleteSupervisorPromptsInput:
    session_id: str


@activity.defn(name="obsolete_supervisor_prompts")
async def obsolete_supervisor_prompts(inp: ObsoleteSupervisorPromptsInput) -> int:
    """Mark all open supervisor prompts for a session as obsolete (clears sticky UI banners)."""
    from shared.database.db import AsyncSessionLocal
    from shared.models.is_models import ISSupervisorPrompt
    from sqlalchemy import update

    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                update(ISSupervisorPrompt)
                .where(ISSupervisorPrompt.session_id == uuid.UUID(inp.session_id))
                .where(ISSupervisorPrompt.status == "open")
                .values(status="obsolete")
            )
            await session.commit()
            count = result.rowcount or 0
            activity.logger.info(
                "  ✅ obsolete_supervisor_prompts | session=%s count=%d",
                inp.session_id,
                count,
            )
            return count
    except Exception as e:
        activity.logger.error("  ❌ obsolete_supervisor_prompts failed: %s", e)
        return 0


@activity.defn(name="mark_supervisor_prompt_answered")
async def mark_supervisor_prompt_answered(inp: MarkSupervisorPromptAnsweredInput) -> str:
    from shared.database.db import AsyncSessionLocal
    from shared.models.is_models import ISSupervisorPrompt
    from sqlalchemy import update

    try:
        async with AsyncSessionLocal() as session:
            await session.execute(
                update(ISSupervisorPrompt)
                .where(ISSupervisorPrompt.id == uuid.UUID(inp.prompt_id))
                .values(status=inp.status, answer_payload=inp.answer_payload)
            )
            await session.commit()
    except Exception as e:
        activity.logger.error("  ❌ mark_supervisor_prompt_answered failed: %s", e)
        return "error"
    return "ok"

