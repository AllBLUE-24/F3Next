"""
File IO — persist_import_run activity.

Persists import plan and execution logs to the v2 normalised schema:
  - is_import_plans  — one per session (3-phase plan)
  - is_import_logs   — one per step/doctype execution
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from temporalio import activity


@dataclass
class PersistImportPlanInput:
    session_id: str
    phases: List[Dict[str, Any]]
    total_steps: int = 0
    plan_r2_path: str = ""
    status: str = "ready"


@dataclass
class PersistImportLogInput:
    import_plan_id: str
    phase: str
    step_number: int
    doctype: str
    action: str
    status: str                     # success | failed | skipped | dry_run
    records_attempted: int = 0
    records_succeeded: int = 0
    records_failed: int = 0
    error_message: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    erpnext_response: Optional[Dict[str, Any]] = None
    duration_seconds: Optional[int] = None


@activity.defn(name="persist_import_plan")
async def persist_import_plan(inp: PersistImportPlanInput) -> str:
    """
    Insert an is_import_plans row.

    Returns: import_plan_id as string (UUID).
    """
    activity.logger.info(
        "▶ persist_import_plan started | session=%s phases=%d steps=%d",
        inp.session_id, len(inp.phases), inp.total_steps,
    )

    from shared.database.db import AsyncSessionLocal
    from shared.models.is_models import ISImportPlan

    plan_id = uuid.uuid4()

    async with AsyncSessionLocal() as session:
        session.add(ISImportPlan(
            id=plan_id,
            session_id=uuid.UUID(inp.session_id),
            total_phases=len(inp.phases),
            total_steps=inp.total_steps,
            plan_r2_path=inp.plan_r2_path or None,
            phases=inp.phases,
            status=inp.status,
        ))
        await session.commit()
        activity.logger.info("  ✅ is_import_plans created %s", plan_id)

    # Audit trail
    from containers.implementation.file_io.persist_audit import log_audit
    await log_audit(
        session_id=inp.session_id,
        action="import_plan_created",
        actor="system",
        entity_type="import_plan",
        entity_id=str(plan_id),
        details={"total_phases": len(inp.phases), "total_steps": inp.total_steps, "status": inp.status},
        result="success",
    )

    activity.logger.info("✅ persist_import_plan done | plan_id=%s", plan_id)
    return str(plan_id)


@activity.defn(name="persist_import_log")
async def persist_import_log(inp: PersistImportLogInput) -> str:
    """
    Insert an is_import_logs row for one execution step.

    Returns: "success"
    """
    activity.logger.info(
        "▶ persist_import_log started | plan=%s phase=%s doctype=%s status=%s",
        inp.import_plan_id, inp.phase, inp.doctype, inp.status,
    )

    from shared.database.db import AsyncSessionLocal
    from shared.models.is_models import ISImportLog

    async with AsyncSessionLocal() as session:
        session.add(ISImportLog(
            id=uuid.uuid4(),
            import_plan_id=uuid.UUID(inp.import_plan_id),
            phase=inp.phase,
            step_number=inp.step_number,
            doctype=inp.doctype,
            action=inp.action,
            status=inp.status,
            records_attempted=inp.records_attempted,
            records_succeeded=inp.records_succeeded,
            records_failed=inp.records_failed,
            error_message=inp.error_message,
            error_details=inp.error_details,
            erpnext_response=inp.erpnext_response,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            duration_seconds=inp.duration_seconds,
        ))
        await session.commit()
        activity.logger.info("  ✅ is_import_logs inserted for %s step %d", inp.phase, inp.step_number)

    activity.logger.info("✅ persist_import_log done")
    return "success"
