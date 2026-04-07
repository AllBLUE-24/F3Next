"""
File IO — persist_import_run activity.

Persists each import phase's execution plan and results to the
is_import_runs Supabase table.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from temporalio import activity


@dataclass
class PersistImportRunInput:
    session_id: str
    phase: str
    execution_plan: Dict[str, Any]
    results: Optional[Dict[str, Any]] = None


@activity.defn(name="persist_import_run")
async def persist_import_run(inp: PersistImportRunInput) -> str:
    """
    Upsert an is_import_runs row for the given phase.

    Returns: "success"
    """
    activity.logger.info(
        "▶ persist_import_run started | session=%s phase=%s",
        inp.session_id, inp.phase,
    )

    from shared.database.db import AsyncSessionLocal
    from shared.models.is_models import ISImportRun
    from sqlalchemy import select, update

    async with AsyncSessionLocal() as session:
        # Check for existing run for this session + phase
        stmt = (
            select(ISImportRun)
            .where(ISImportRun.session_id == uuid.UUID(inp.session_id))
            .where(ISImportRun.phase == inp.phase)
        )
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            update_vals: Dict[str, Any] = {"execution_plan": inp.execution_plan}
            if inp.results is not None:
                update_vals["results"] = inp.results
                update_vals["completed_at"] = datetime.utcnow()
            await session.execute(
                update(ISImportRun)
                .where(ISImportRun.id == existing.id)
                .values(**update_vals)
            )
        else:
            new_run = ISImportRun(
                id=uuid.uuid4(),
                session_id=uuid.UUID(inp.session_id),
                phase=inp.phase,
                execution_plan=inp.execution_plan,
                results=inp.results,
            )
            if inp.results is not None:
                new_run.completed_at = datetime.utcnow()
            session.add(new_run)

        await session.commit()
        activity.logger.info("  ✅ is_import_runs upserted for phase %s", inp.phase)

    activity.logger.info("✅ persist_import_run done | phase=%s", inp.phase)
    return "success"
