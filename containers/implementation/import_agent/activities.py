"""
Import Agent — Temporal activities for the 3-phase ERPNext import.

Activities read state from Supabase/R2 and persist results back.
Temporal only sees tiny string returns.
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
    Read target structure + validation status from Supabase, build the
    3-phase import plan, persist to R2 + Supabase.

    Returns: "ready" or "blocked"
    """
    activity.logger.info("▶ build_import_plan started | session=%s", inp.session_id)

    from shared.database.db import AsyncSessionLocal
    from shared.models.is_models import ISSession, ISMapping, ISImportRun
    from sqlalchemy import select, update

    # ── 1. Read from Supabase ────────────────────────────────────────────────
    async with AsyncSessionLocal() as session:
        stmt = select(ISSession).where(ISSession.id == uuid.UUID(inp.session_id))
        result = await session.execute(stmt)
        is_session = result.scalar_one_or_none()

        if not is_session:
            activity.logger.error("  ❌ Session %s not found", inp.session_id)
            return "error:session_not_found"

        target_structure = is_session.target_structure or {}

        # Get mapped doctypes
        stmt = select(ISMapping).where(ISMapping.session_id == uuid.UUID(inp.session_id))
        result = await session.execute(stmt)
        mappings = result.scalars().all()

    mapped_doctypes = [m.doctype_name for m in mappings]
    
    # Check overall validation status
    validation_status = "pass"
    for m in mappings:
        if m.status == "failed":
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

    # ── 4. Create import run records in Supabase ─────────────────────────────
    if plan_status == "ready":
        async with AsyncSessionLocal() as session:
            for phase_def in plan.get("phases", []):
                new_run = ISImportRun(
                    id=uuid.uuid4(),
                    session_id=uuid.UUID(inp.session_id),
                    phase=phase_def["phase"],
                    execution_plan=phase_def,
                )
                session.add(new_run)
            await session.commit()
            activity.logger.info("  ✅ is_import_runs created for %d phases", len(plan.get("phases", [])))

    activity.logger.info("✅ build_import_plan done | status=%s total_steps=%s",
                         plan_status, plan.get("total_steps"))
    return plan_status


@activity.defn(name="execute_import_phase")
async def execute_import_phase(inp: ExecutePhaseInput) -> str:
    """
    Execute (or dry-run) a single import phase.
    
    Reads the execution plan from is_import_runs, downloads row data from R2,
    executes against ERPNext API, then persists results back to Supabase.

    Returns: "success" or "error"
    """
    activity.logger.info("▶ execute_import_phase started | session=%s phase=%s dry_run=%s",
                         inp.session_id, inp.phase_id, inp.dry_run)

    from shared.database.db import AsyncSessionLocal
    from shared.models.is_models import ISImportRun, ISMapping
    from sqlalchemy import select, update

    # ── 1. Read execution plan from Supabase ─────────────────────────────────
    async with AsyncSessionLocal() as session:
        stmt = (
            select(ISImportRun)
            .where(ISImportRun.session_id == uuid.UUID(inp.session_id))
            .where(ISImportRun.phase == inp.phase_id)
        )
        result = await session.execute(stmt)
        import_run = result.scalar_one_or_none()

    if not import_run:
        activity.logger.error("  ❌ Import run not found for phase %s", inp.phase_id)
        return "error:not_found"

    plan = import_run.execution_plan or {}
    steps = plan.get("steps", [])

    # ── 2. For each step, download data from R2 if needed ────────────────────
    s3 = _get_s3_client()
    slug = inp.company_slug or "unknown"
    results = []

    for step in steps:
        dt = step.get("doctype", "")
        action = step.get("action", "")

        if action == "default_or_skip":
            results.append({"doctype": dt, "status": "skipped"})
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
            continue

        if inp.dry_run or not inp.erpnext_base_url:
            results.append({
                "doctype": dt,
                "status": "dry_run",
                "would_create": len(rows),
            })
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
        except Exception as exc:
            results.append({"doctype": dt, "status": "error", "detail": str(exc)})

    # ── 3. Persist results back to Supabase ──────────────────────────────────
    phase_result = {
        "phase": inp.phase_id,
        "results": results,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }

    async with AsyncSessionLocal() as session:
        await session.execute(
            update(ISImportRun)
            .where(ISImportRun.id == import_run.id)
            .values(
                results=phase_result,
                completed_at=datetime.utcnow(),
            )
        )
        await session.commit()
        activity.logger.info("  ✅ is_import_runs updated for phase %s", inp.phase_id)

    activity.logger.info("✅ execute_import_phase done | phase=%s", inp.phase_id)
    return "success"