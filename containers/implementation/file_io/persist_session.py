"""
File IO — persist_session activity.

Creates or updates an IS session row in Supabase (is_sessions table).
This is the single source of truth for workflow state — Temporal only
stores the session_id string.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from temporalio import activity


@dataclass
class PersistSessionInput:
    project_id: str
    workflow_id: str
    status: str = "awaiting_files"
    f3iche_profile: Optional[Dict[str, Any]] = None
    target_structure: Optional[Dict[str, Any]] = None


@activity.defn(name="persist_session")
async def persist_session(inp: PersistSessionInput) -> str:
    """
    Upsert an is_sessions row.

    - On first call (workflow start): creates the row, returns new session_id.
    - On subsequent calls: updates status / profile / target_structure.

    Returns: session_id as a string (UUID).
    """
    activity.logger.info(
        "▶ persist_session started | project=%s workflow=%s status=%s",
        inp.project_id, inp.workflow_id, inp.status,
    )

    from shared.database.db import AsyncSessionLocal
    from shared.models.is_models import ISSession
    from sqlalchemy import select, update

    async with AsyncSessionLocal() as session:
        # Check if session already exists for this workflow
        stmt = select(ISSession).where(ISSession.workflow_id == inp.workflow_id)
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            # Update existing session
            update_vals: Dict[str, Any] = {"status": inp.status}
            if inp.f3iche_profile is not None:
                update_vals["f3iche_profile"] = inp.f3iche_profile
            if inp.target_structure is not None:
                update_vals["target_structure"] = inp.target_structure

            await session.execute(
                update(ISSession)
                .where(ISSession.id == existing.id)
                .values(**update_vals)
            )
            await session.commit()
            session_id = str(existing.id)
            activity.logger.info("  ✅ Updated existing session %s", session_id)
        else:
            # Create new session
            new_id = uuid.uuid4()
            new_session = ISSession(
                id=new_id,
                project_id=uuid.UUID(inp.project_id),
                workflow_id=inp.workflow_id,
                status=inp.status,
                f3iche_profile=inp.f3iche_profile,
                target_structure=inp.target_structure,
            )
            session.add(new_session)
            await session.commit()
            session_id = str(new_id)
            activity.logger.info("  ✅ Created new session %s", session_id)

    activity.logger.info("✅ persist_session done | session_id=%s", session_id)
    return session_id
