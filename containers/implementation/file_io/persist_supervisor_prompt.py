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
    return str(prompt_id)


@dataclass
class MarkSupervisorPromptAnsweredInput:
    prompt_id: str
    answer_payload: Dict[str, Any] = field(default_factory=dict)
    status: str = "answered"


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

