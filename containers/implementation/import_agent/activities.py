"""
Import Agent — Temporal activities for the 3-phase ERPNext import.

v2: Uses ISImportPlan + ISImportLog (not ISImportRun).
    Reads target structure from ISTargetStructure.
    Reads mapped data from ISMappedData.
"""
from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import boto3
from botocore.config import Config
from temporalio import activity


def _get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=os.getenv("R2_ENDPOINT"),
        aws_access_key_id=os.getenv("R2_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("R2_SECRET_ACCESS_KEY"),
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )


# ── Embedded service logic ────────────────────────────────────────────────────

class _ImportEngine:
    PHASE_A_DOCTYPES = [
        "Company", "Fiscal Year", "Currency", "UOM",
        "Account", "Item Group", "Customer Group", "Supplier Group",
        "Warehouse", "Tax Template",
    ]
    PHASE_B_DOCTYPES = ["Item", "Customer", "Supplier", "Item Price", "BOM"]
    PHASE_C_DOCTYPES = ["Stock Entry", "Journal Entry", "Purchase Invoice", "Sales Invoice", "Payment Entry"]

    def build_plan(
        self,
        target_structure: Dict,
        mapped_doctypes: List[str],
        validation_status: str,
    ) -> Dict[str, Any]:
        if validation_status == "fail":
            return {
                "status": "blocked",
                "reason": "Validation failed. Fix errors before import.",
            }

        required = target_structure.get("required_doctypes", [])
        phases = []

        def _phase(phase_id: str, name: str, desc: str, doctypes: List[str], filter_required: bool = False) -> Dict:
            steps = []
            for dt in doctypes:
                if filter_required and dt not in required:
                    continue
                steps.append({
                    "doctype": dt,
                    "action": "create" if dt in mapped_doctypes else "default_or_skip",
                })
            return {"phase": phase_id, "name": name, "description": desc, "doctypes": doctypes, "steps": steps}

        phases.append(_phase(
            "phase_a_config", "Configuration Setup",
            "COA, Groups, Warehouses, Tax Templates, Fiscal Year, Company settings",
            self.PHASE_A_DOCTYPES,
        ))
        phases.append(_phase(
            "phase_b_master", "Master Data",
            "Items, Customers, Suppliers, BOMs (manufacturing only)",
            self.PHASE_B_DOCTYPES,
            filter_required=True,
        ))
        phases.append(_phase(
            "phase_c_transactional", "Transactional Data",
            "Opening balances, historical transactions (last 3 months optional)",
            self.PHASE_C_DOCTYPES,
        ))

        return {
            "status": "ready",
            "phases": phases,
            "total_steps": sum(len(p["steps"]) for p in phases),
        }


# ── Input dataclasses ────────────────────────────────────────────────────────

@dataclass
class BuildImportPlanInput:
    session_id: str
    project_id: str
    company_slug: str = "unknown"


@dataclass
class ExecutePhaseInput:
    session_id: str
    phase_id: str
    project_id: str
    company_slug: str = "unknown"
    dry_run: bool = True
    erpnext_base_url: Optional[str] = None
    erpnext_api_key: Optional[str] = None


# ── Activity definitions ─────────────────────────────────────────────────────

@activity.defn(name="build_import_plan")
async def build_import_plan(inp: BuildImportPlanInput) -> str:
    """
    Read target structure from ISTargetStructure + validation status from ISMappedData,
    build the 3-phase import plan, persist to ISImportPlan + R2.

    Returns: "ready" or "blocked"
    """
    activity.logger.info("▶ build_import_plan started | session=%s", inp.session_id)

    from shared.database.db import AsyncSessionLocal
    from shared.models.is_models import ISTargetStructure, ISMappedData, ISImportPlan
    from sqlalchemy import select

    # ── 1. Read from Supabase (v2 tables) ────────────────────────────────────
    async with AsyncSessionLocal() as session:
        # Get latest target structure
        stmt = (
            select(ISTargetStructure)
            .where(ISTargetStructure.session_id == uuid.UUID(inp.session_id))
            .order_by(ISTargetStructure.created_at.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        target_row = result.scalar_one_or_none()

        if not target_row:
            activity.logger.error("  ❌ No target structure for session %s", inp.session_id)
            return "error:no_target_structure"

        target_structure = {
            "required_doctypes": target_row.required_doctypes or [],
        }

        # Get mapped data
        stmt = select(ISMappedData).where(ISMappedData.session_id == uuid.UUID(inp.session_id))
        result = await session.execute(stmt)
        mapped_data_rows = result.scalars().all()

    mapped_doctypes = [md.target_doctype for md in mapped_data_rows]
    
    # Check overall validation status
    validation_status = "pass"
    for md in mapped_data_rows:
        if md.validation_status == "failed":
            validation_status = "fail"
            break

    activity.logger.info("  target=%d doctypes, mapped=%d, validation=%s",
                         len(target_structure.get("required_doctypes", [])),
                         len(mapped_doctypes), validation_status)

    # ── 2. Build plan ────────────────────────────────────────────────────────
    engine = _ImportEngine()
    plan = engine.build_plan(target_structure, mapped_doctypes, validation_status)
    plan_status = plan.get("status", "blocked")

    # ── 3. Persist plan to R2 ────────────────────────────────────────────────
    slug = inp.company_slug or "unknown"
    plan_key = f"{slug}/{inp.project_id}/_import_plan/plan.json"
    try:
        s3 = _get_s3_client()
        s3.put_object(
            Bucket="clean-data",
            Key=plan_key,
            Body=json.dumps(plan, indent=2, default=str).encode("utf-8"),
            ContentType="application/json",
        )
        activity.logger.info("  ✅ R2 uploaded: clean-data/%s", plan_key)
    except Exception as e:
        activity.logger.error("  ❌ R2 plan upload failed: %s", e)

    # ── 4. Create ISImportPlan in Supabase ───────────────────────────────────
    plan_id = uuid.uuid4()
    if plan_status == "ready":
        async with AsyncSessionLocal() as session:
            session.add(ISImportPlan(
                id=plan_id,
                session_id=uuid.UUID(inp.session_id),
                total_phases=len(plan.get("phases", [])),
                total_steps=plan.get("total_steps", 0),
                plan_r2_path=plan_key,
                phases=plan.get("phases", []),
                status="ready",
            ))
            await session.commit()
            activity.logger.info("  ✅ is_import_plans created %s", plan_id)

    # ── 5. Audit trail ───────────────────────────────────────────────────────
    from containers.implementation.file_io.persist_audit import log_audit
    await log_audit(
        session_id=inp.session_id,
        action="import_plan_created",
        actor="system",
        entity_type="import_plan",
        entity_id=str(plan_id),
        details={"status": plan_status, "total_steps": plan.get("total_steps")},
        result="success",
    )

    activity.logger.info("✅ build_import_plan done | status=%s total_steps=%s",
                         plan_status, plan.get("total_steps"))
    return plan_status


@activity.defn(name="execute_import_phase")
async def execute_import_phase(inp: ExecutePhaseInput) -> str:
    """
    Execute (or dry-run) a single import phase.
    
    v2: Reads from ISImportPlan. Writes ISImportLog entries per step.

    Returns: "success" or "error"
    """
    activity.logger.info("▶ execute_import_phase started | session=%s phase=%s dry_run=%s",
                         inp.session_id, inp.phase_id, inp.dry_run)

    from shared.database.db import AsyncSessionLocal
    from shared.models.is_models import ISImportPlan, ISImportLog
    from sqlalchemy import select, update

    # ── 1. Read import plan from Supabase ────────────────────────────────────
    async with AsyncSessionLocal() as session:
        stmt = (
            select(ISImportPlan)
            .where(ISImportPlan.session_id == uuid.UUID(inp.session_id))
            .order_by(ISImportPlan.created_at.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        import_plan = result.scalar_one_or_none()

    if not import_plan:
        activity.logger.error("  ❌ Import plan not found for session %s", inp.session_id)
        return "error:not_found"

    # Find the phase in the plan
    phases = import_plan.phases or []
    phase_def = next((p for p in phases if p.get("phase") == inp.phase_id), None)
    if not phase_def:
        activity.logger.error("  ❌ Phase %s not found in plan", inp.phase_id)
        return "error:phase_not_found"

    steps = phase_def.get("steps", [])

    # Update plan status
    async with AsyncSessionLocal() as session:
        await session.execute(
            update(ISImportPlan)
            .where(ISImportPlan.id == import_plan.id)
            .values(status="executing", current_phase=inp.phase_id)
        )
        await session.commit()

    # ── 2. For each step, download data from R2 if needed ────────────────────
    s3 = _get_s3_client()
    slug = inp.company_slug or "unknown"
    results = []

    for step_idx, step in enumerate(steps):
        dt = step.get("doctype", "")
        action = step.get("action", "")
        step_start = datetime.utcnow()

        if action == "default_or_skip":
            results.append({"doctype": dt, "status": "skipped"})
            # Log entry
            async with AsyncSessionLocal() as session:
                session.add(ISImportLog(
                    id=uuid.uuid4(),
                    import_plan_id=import_plan.id,
                    phase=inp.phase_id,
                    step_number=step_idx + 1,
                    doctype=dt,
                    action=action,
                    status="skipped",
                    started_at=step_start,
                    completed_at=datetime.utcnow(),
                ))
                await session.commit()
            continue

        # Download extracted rows from R2
        rows_key = f"{slug}/{inp.project_id}/mappings/extracted_rows/{dt}.json"
        rows = []
        try:
            response = s3.get_object(Bucket="clean-data", Key=rows_key)
            rows = json.loads(response["Body"].read().decode("utf-8"))
        except Exception:
            activity.logger.info("  No R2 data for %s — skipping", dt)
            results.append({"doctype": dt, "status": "skipped", "detail": "No data in R2"})
            async with AsyncSessionLocal() as session:
                session.add(ISImportLog(
                    id=uuid.uuid4(),
                    import_plan_id=import_plan.id,
                    phase=inp.phase_id,
                    step_number=step_idx + 1,
                    doctype=dt,
                    action=action,
                    status="skipped",
                    error_message="No data in R2",
                    started_at=step_start,
                    completed_at=datetime.utcnow(),
                ))
                await session.commit()
            continue

        if inp.dry_run or not inp.erpnext_base_url:
            results.append({
                "doctype": dt,
                "status": "dry_run",
                "would_create": len(rows),
            })
            async with AsyncSessionLocal() as session:
                session.add(ISImportLog(
                    id=uuid.uuid4(),
                    import_plan_id=import_plan.id,
                    phase=inp.phase_id,
                    step_number=step_idx + 1,
                    doctype=dt,
                    action=action,
                    status="dry_run",
                    records_attempted=len(rows),
                    started_at=step_start,
                    completed_at=datetime.utcnow(),
                ))
                await session.commit()
            continue

        # ── Live ERPNext import ──────────────────────────────────────────
        import httpx
        try:
            async with httpx.AsyncClient(base_url=inp.erpnext_base_url, timeout=30.0) as client:
                resp = await client.post(
                    f"/api/resource/{dt}",
                    json={"data": rows},
                    headers={"Authorization": f"token {inp.erpnext_api_key}"},
                )
                resp.raise_for_status()
                results.append({"doctype": dt, "status": "created", "count": len(rows)})
                async with AsyncSessionLocal() as session:
                    session.add(ISImportLog(
                        id=uuid.uuid4(),
                        import_plan_id=import_plan.id,
                        phase=inp.phase_id,
                        step_number=step_idx + 1,
                        doctype=dt,
                        action=action,
                        status="success",
                        records_attempted=len(rows),
                        records_succeeded=len(rows),
                        started_at=step_start,
                        completed_at=datetime.utcnow(),
                    ))
                    await session.commit()
        except Exception as exc:
            results.append({"doctype": dt, "status": "error", "detail": str(exc)})
            async with AsyncSessionLocal() as session:
                session.add(ISImportLog(
                    id=uuid.uuid4(),
                    import_plan_id=import_plan.id,
                    phase=inp.phase_id,
                    step_number=step_idx + 1,
                    doctype=dt,
                    action=action,
                    status="failed",
                    records_attempted=len(rows),
                    records_failed=len(rows),
                    error_message=str(exc),
                    started_at=step_start,
                    completed_at=datetime.utcnow(),
                ))
                await session.commit()

    # ── 3. Update import plan status ─────────────────────────────────────────
    async with AsyncSessionLocal() as session:
        await session.execute(
            update(ISImportPlan)
            .where(ISImportPlan.id == import_plan.id)
            .values(
                current_phase=inp.phase_id,
                current_step=len(steps),
            )
        )
        await session.commit()

    # ── 4. Audit trail ───────────────────────────────────────────────────────
    from containers.implementation.file_io.persist_audit import log_audit
    await log_audit(
        session_id=inp.session_id,
        action="import_executed",
        actor="system",
        entity_type="import",
        details={"phase": inp.phase_id, "steps": len(steps), "results": results},
        result="success",
    )

    activity.logger.info("✅ execute_import_phase done | phase=%s", inp.phase_id)
    return "success"