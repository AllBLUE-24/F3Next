"""
File IO — persist_session activity.

Creates or updates an IS session row in Supabase (is_sessions table).
Slimmed for v2 schema — no more JSONB profile/target blobs.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, Dict, Optional

from temporalio import activity


@dataclass
class PersistSessionInput:
    project_id: str
    workflow_id: str
    status: str = "awaiting_files"
    discovery_f3iche: Optional[str] = None
    discovery_industry: Optional[str] = None
    discovery_company_size: Optional[str] = None


@activity.defn(name="persist_session")
async def persist_session(inp: PersistSessionInput) -> str:
    """
    Upsert an is_sessions row.

    - On first call (workflow start): creates the row, returns new session_id.
    - On subsequent calls: updates status.

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
            if inp.discovery_f3iche is not None:
                update_vals["discovery_f3iche"] = inp.discovery_f3iche
            if inp.discovery_industry is not None:
                update_vals["discovery_industry"] = inp.discovery_industry
            if inp.discovery_company_size is not None:
                update_vals["discovery_company_size"] = inp.discovery_company_size

            # Mark completed_at when status is 'complete'
            if inp.status == "complete":
                from datetime import datetime
                update_vals["completed_at"] = datetime.utcnow()

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
                discovery_f3iche=inp.discovery_f3iche,
                discovery_industry=inp.discovery_industry,
                discovery_company_size=inp.discovery_company_size,
            )
            session.add(new_session)
            await session.commit()
            session_id = str(new_id)
            activity.logger.info("  ✅ Created new session %s", session_id)

    # Audit trail
    from containers.implementation.file_io.persist_audit import log_audit
    await log_audit(
        session_id=session_id,
        action="session_created" if not existing else "session_updated",
        actor="temporal_workflow",
        details={"status": inp.status},
        result="success",
    )

    activity.logger.info("✅ persist_session done | session_id=%s", session_id)
    return session_id
