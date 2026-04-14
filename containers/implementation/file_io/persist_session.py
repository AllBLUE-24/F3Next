"""
File IO Agent — Temporal activities for session persistence.

Creates, updates, and completes the ISSession record in Supabase.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from temporalio import activity
from sqlalchemy import select, update

from shared.database.db import AsyncSessionLocal
from shared.models.is_models import ISSession


# ─── DATACLASSES ──────────────────────────────────────────────────────────────

@dataclass
class CompleteSessionInput:
    session_id: str
    status: str = "complete"

@dataclass
class PersistSessionInput:
    project_id: str
    workflow_id: str
    status: str
    discovery_f3iche: Optional[str] = None
    discovery_industry: Optional[str] = None
    discovery_company_size: Optional[str] = None


# ─── ACTIVITIES ───────────────────────────────────────────────────────────────

@activity.defn(name="persist_session")
async def persist_session(inp: Any) -> Any:
    """
    Handles both session creation (PersistSessionInput) and completion (CompleteSessionInput).
    We use 'Any' for the input type because Temporal SDK allows passing either dataclass
    when defined this way, avoiding signature mismatch errors.
    """
    # Convert dict to object if necessary (Temporal passes dict when type hint is Any)
    if isinstance(inp, dict):
        if "session_id" in inp:
            inp = CompleteSessionInput(**inp)
        elif "project_id" in inp:
            inp = PersistSessionInput(**inp)
        else:
            raise ValueError(f"Invalid input dictionary passed to persist_session: {inp}")

    # ── COMPLETE SESSION ──
    if isinstance(inp, CompleteSessionInput):
        activity.logger.info("▶ persist_session [Complete] started | session=%s", inp.session_id)
        completed_at = datetime.utcnow()
        duration_minutes = 0

        try:
            async with AsyncSessionLocal() as session:
                stmt = select(ISSession).where(ISSession.id == uuid.UUID(inp.session_id))
                result = await session.execute(stmt)
                session_row = result.scalar_one_or_none()

                if session_row and session_row.created_at:
                    start_time = session_row.created_at.replace(tzinfo=None)
                    duration = completed_at - start_time
                    duration_minutes = max(1, int(duration.total_seconds() / 60))

                await session.execute(
                    update(ISSession)
                    .where(ISSession.id == uuid.UUID(inp.session_id))
                    .values(
                        status=inp.status,
                        completed_at=completed_at,
                        updated_at=completed_at
                    )
                )
                await session.commit()
                activity.logger.info("  ✅ is_sessions updated to '%s'", inp.status)

            from containers.implementation.file_io.persist_audit import log_audit
            await log_audit(
                session_id=inp.session_id,
                action="session_completed",
                actor="system",
                entity_type="session",
                entity_id=inp.session_id,
                details={"total_duration_minutes": duration_minutes},
                result="success"
            )

        except Exception as e:
            activity.logger.error("  ❌ Failed to persist session completion: %s", e)
            return {"session_id": inp.session_id, "status": "error", "error": str(e)}

        activity.logger.info("✅ persist_session [Complete] done | duration=%d mins", duration_minutes)
        return {"session_id": inp.session_id, "status": inp.status, "completed_at": completed_at.isoformat() + "Z"}

    # ── CREATE / UPDATE SESSION ──
    elif isinstance(inp, PersistSessionInput):
        activity.logger.info("▶ persist_session [Create/Update] started | project=%s status=%s", inp.project_id, inp.status)
        session_id_str = ""
        
        try:
            async with AsyncSessionLocal() as session:
                stmt = select(ISSession).where(ISSession.project_id == uuid.UUID(inp.project_id))
                result = await session.execute(stmt)
                existing = result.scalar_one_or_none()
                
                if existing:
                    # Update status
                    session_id_str = str(existing.id)
                    existing.status = inp.status
                    existing.updated_at = datetime.utcnow()
                    await session.commit()
                    activity.logger.info("  ✅ is_sessions updated to '%s'", inp.status)
                else:
                    # Create new
                    new_session = ISSession(
                        id=uuid.uuid4(),
                        project_id=uuid.UUID(inp.project_id),
                        workflow_id=inp.workflow_id,
                        status=inp.status,
                        discovery_f3iche=inp.discovery_f3iche,
                        discovery_industry=inp.discovery_industry,
                        discovery_company_size=inp.discovery_company_size
                    )
                    session.add(new_session)
                    await session.commit()
                    session_id_str = str(new_session.id)
                    activity.logger.info("  ✅ is_sessions created | session=%s", session_id_str)
                    
                    # Log Audit Trail for creation
                    from containers.implementation.file_io.persist_audit import log_audit
                    await log_audit(
                        session_id=session_id_str,
                        action="session_started",
                        actor="system",
                        entity_type="session",
                        entity_id=session_id_str,
                        details={"workflow_id": inp.workflow_id},
                        result="success"
                    )

        except Exception as e:
            activity.logger.error("  ❌ Failed to create/update session: %s", e)
            raise e
            
        return session_id_str

    else:
        raise ValueError("Invalid input type passed to persist_session")
