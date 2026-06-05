"""Load discovery chat + metadata for IS synthesis steps."""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession


def _transcript_from_chat_history(chat_history: Any, *, max_chars: int = 4000) -> str:
    messages: List[Dict[str, str]] = []
    if isinstance(chat_history, list):
        messages = [m for m in chat_history if isinstance(m, dict)]
    elif isinstance(chat_history, dict):
        messages = [m for m in (chat_history.get("messages") or []) if isinstance(m, dict)]

    lines: List[str] = []
    for msg in messages[-20:]:
        role = str(msg.get("role") or "user").strip()
        content = str(msg.get("content") or "").strip()
        if content:
            lines.append(f"{role}: {content}")
    transcript = "\n".join(lines)
    return transcript[:max_chars] if transcript else ""


async def load_discovery_context(
    db: AsyncSession,
    *,
    project_id: str,
    session_row: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Load discovery metadata + chat transcript from hooks and session fallbacks.

    Returns:
        discovery_metadata, chat_transcript, discovery_f3iche, discovery_industry, mvp_focus
    """
    pid = uuid.UUID(str(project_id)) if not isinstance(project_id, uuid.UUID) else project_id

    discovery_metadata: Dict[str, Any] = {}
    chat_transcript = ""

    try:
        stmt = text(
            "SELECT discovery_metadata, chat_history FROM hooks "
            "WHERE project_id = :pid ORDER BY created_at DESC LIMIT 1"
        )
        row = (await db.execute(stmt, {"pid": pid})).fetchone()
        if row:
            if row[0] and isinstance(row[0], dict):
                discovery_metadata = row[0]
            chat_transcript = _transcript_from_chat_history(row[1])
    except Exception:
        pass

    discovery_f3iche = discovery_metadata.get("f3iche")
    discovery_industry = discovery_metadata.get("industry")
    mvp_focus = discovery_metadata.get("mvp_focus")

    if session_row:
        discovery_f3iche = discovery_f3iche or getattr(session_row, "discovery_f3iche", None)
        discovery_industry = discovery_industry or getattr(session_row, "discovery_industry", None)
        mvp_focus = mvp_focus or getattr(session_row, "mvp_focus", None)

    return {
        "discovery_metadata": discovery_metadata,
        "chat_transcript": chat_transcript,
        "discovery_f3iche": discovery_f3iche,
        "discovery_industry": discovery_industry,
        "mvp_focus": mvp_focus,
        "headline": discovery_metadata.get("headline"),
        "reasoning": discovery_metadata.get("reasoning"),
        "fit_score": discovery_metadata.get("fit_score"),
    }
