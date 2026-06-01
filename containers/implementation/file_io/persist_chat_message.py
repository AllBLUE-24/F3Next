"""
File IO — persist_chat_message activity.

Stores IS assistant chat messages for the right-panel conversation UI.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from temporalio import activity


@dataclass
class PersistChatMessageInput:
    session_id: str
    step: str
    role: str  # user | assistant | system
    content: str
    message_type: str = "chat"
    message_metadata: Optional[Dict[str, Any]] = None


async def save_chat_message(
    session_id: str,
    step: str,
    role: str,
    content: str,
    *,
    message_type: str = "chat",
    message_metadata: Optional[Dict[str, Any]] = None,
) -> str:
    """Insert a chat message row; usable from API layer and Temporal activities."""
    from shared.database.db import AsyncSessionLocal
    from shared.models.is_models import ISChatMessage

    msg_id = uuid.uuid4()
    async with AsyncSessionLocal() as session:
        session.add(
            ISChatMessage(
                id=msg_id,
                session_id=uuid.UUID(session_id),
                step=step,
                role=role,
                content=content,
                message_type=message_type,
                message_metadata=message_metadata,
            )
        )
        await session.commit()
    return str(msg_id)


@activity.defn(name="persist_chat_message")
async def persist_chat_message(inp: PersistChatMessageInput) -> str:
    try:
        return await save_chat_message(
            inp.session_id,
            inp.step,
            inp.role,
            inp.content,
            message_type=inp.message_type,
            message_metadata=inp.message_metadata,
        )
    except Exception as e:
        activity.logger.error("  ❌ persist_chat_message failed: %s", e)
        return "error"


def format_auto_fix_chat_message(applied: list) -> str:
    """Build a user-visible summary of supervisor auto-fixes."""
    if not applied:
        return ""

    parts: list[str] = []
    for item in applied:
        doctype = item.get("doctype") or "record"
        op = item.get("op") or "fix"
        updated = item.get("updated")
        if op == "apply_kb_defaults":
            parts.append(f"Applied KB defaults for **{doctype}**")
        elif op == "map_enum":
            parts.append(f"Normalized enum values on **{doctype}** ({updated or 0} rows)")
        elif op == "strip_units":
            parts.append(f"Stripped units from numeric fields on **{doctype}** ({updated or 0} rows)")
        else:
            parts.append(f"Applied {op} on **{doctype}**")

    if len(parts) == 1:
        return f"I automatically applied a fix: {parts[0]}."
    return "I automatically applied these fixes:\n" + "\n".join(f"• {p}" for p in parts)
