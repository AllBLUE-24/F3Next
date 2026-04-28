"""
Import Agent — Temporal activities for the 3-phase ERPNext import.

Prerequisite planning is done in target_agent (Step 8). Each setup_step
arrives here with an `action` field set by the planner:
  - must_create          → user has a data file  → action: create
  - use_default          → baseline values exist  → action: seed_from_baseline
  - auto_created_by_erpnext → ERPNext handles it → action: skip
  - must_create (no file)→ data gap              → action: data_gap

The Pre-flight Seeder runs before row-level import to POST all
`seed_from_baseline` doctypes so link-validation never fails.
"""
from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import boto3
import httpx
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


# ── Knowledge base path ───────────────────────────────────────────────────────

_KB_DIR = Path(__file__).resolve().parent.parent.parent / "knowledge_base" / "erpnext"
_BASELINE_PATH = _KB_DIR / "erpnext_deafaults_baseline.json"


# ── Baseline seeder helpers ───────────────────────────────────────────────────

# Maps each doctype to the field name Frappe uses as the primary identifier.
# Used when building the POST body for a baseline seed record.
_DT_NAME_FIELD: Dict[str, str] = {
    "UOM":              "uom_name",
    "Item Group":       "item_group_name",
    "Customer Group":   "customer_group_name",
    "Supplier Group":   "supplier_group_name",
    "Territory":        "territory_name",
    "Price List":       "price_list_name",
    "Currency":         "currency_name",
    "Country":          "country_name",
    "Department":       "department_name",
    "Designation":      "designation_name",
    "Sales Stage":      "stage_name",
    "Lead Source":      "source_name",
    "Incoterm":         "incoterm",
    "Industry Type":    "industry",
    "Item Attribute":   "attribute_name",
    "Fiscal Year":      "year",
    "Sales Person":     "sales_person_name",
}


def _build_baseline_record(doctype: str, value: str) -> Dict[str, Any]:
    """
    Build the minimal POST body required to create a baseline seed record
    in ERPNext via the Frappe REST API.

    For most simple master doctypes (UOM, Item Group, Territory, etc.) only
    the name field is required. Special cases are handled explicitly.
    """
    name_field = _DT_NAME_FIELD.get(doctype)
    if name_field:
        return {name_field: value}

    # Generic fallback: try snake_case of doctype + "_name"
    snake = doctype.lower().replace(" ", "_")
    return {f"{snake}_name": value}


# ── Embedded service logic ────────────────────────────────────────────────────

class _ImportEngine:
    def build_plan(
        self,
        setup_steps: List[Dict],
        mapped_data_dict: Dict[str, Dict],
        validation_status: str,
    ) -> Dict[str, Any]:
        
        if validation_status == "fail":
            return {
                "status": "blocked",
                "reason": "Validation failed. Fix errors before import.",
            }

        phases = {
            "phase_a_config": {"name": "Configuration Setup", "steps": []},
            "phase_b_master": {"name": "Master Data", "steps": []},
            "phase_c_transactional": {"name": "Transactional Data", "steps": []}
        }
        
        total_steps = 0
        
        for step_idx, step_info in enumerate(setup_steps):
            dt = step_info.get("doctype", "Unknown")
            phase_key = step_info.get("phase", "phase_a_config")

            if phase_key not in phases:
                phase_key = "phase_a_config"

            is_mapped = dt in mapped_data_dict
            # Read the planner's action from Step 8 — do NOT discard it
            planner_action = step_info.get("action", "must_create")

            if is_mapped:
                # User has provided a data file — import it row by row
                exec_action  = "create"
                data_source  = mapped_data_dict[dt]["r2_path"]
                record_count = mapped_data_dict[dt]["total_rows"]
            elif planner_action == "use_default":
                # Values exist in erpnext_deafaults_baseline.json — seed them
                exec_action  = "seed_from_baseline"
                data_source  = "baseline"
                record_count = 0  # will be filled in at seed time
            elif planner_action == "auto_created_by_erpnext":
                # ERPNext creates these automatically on Company setup — skip
                exec_action  = "skip"
                data_source  = "auto"
                record_count = 0
            else:
                # must_create but no file uploaded — flag as data gap
                exec_action  = "data_gap"
                data_source  = "none"
                record_count = 0

            step_def = {
                "step":        step_idx + 1,
                "doctype":     dt,
                "action":      exec_action,
                "data_source": data_source,
                "records":     record_count,
            }

            phases[phase_key]["steps"].append(step_def)
            total_steps += 1

        return {
            "status": "ready",
            "total_phases": len([p for p in phases.values() if len(p["steps"]) > 0]),
            "total_steps": total_steps,
            "estimated_duration_minutes": max(5, int(total_steps * 0.5)),
            "phases": phases,
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
    dry_run: bool = False  # Default to live execution — safety is via double-confirm signals
    erpnext_base_url: Optional[str] = None
    erpnext_api_key: Optional[str] = None


# ── Activity definitions ─────────────────────────────────────────────────────

@activity.defn(name="build_import_plan")
async def build_import_plan(inp: BuildImportPlanInput) -> str:
    """
    Step 12: Generates the 3-Phase execution plan from the already-resolved
    ISTargetStructure (setup_steps are graph-authoritative from Step 8).
    """
    activity.logger.info("▶ build_import_plan started | session=%s", inp.session_id)

    from shared.database.db import AsyncSessionLocal
    from shared.models.is_models import ISTargetStructure, ISMappedData, ISImportPlan
    from sqlalchemy import select

    setup_steps = []
    
    async with AsyncSessionLocal() as session:
        stmt = (
            select(ISTargetStructure)
            .where(ISTargetStructure.session_id == uuid.UUID(inp.session_id))
            .order_by(ISTargetStructure.created_at.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        target_row = result.scalar_one_or_none()

        if not target_row:
            return "error:no_target_structure"

        try:
            setup_steps = json.loads(target_row.setup_steps) if isinstance(target_row.setup_steps, str) else target_row.setup_steps
        except Exception:
            setup_steps = []

        stmt = select(ISMappedData).where(ISMappedData.session_id == uuid.UUID(inp.session_id))
        result = await session.execute(stmt)
        mapped_data_rows = result.scalars().all()

    mapped_data_dict = {}
    validation_status = "pass"
    
    for md in mapped_data_rows:
        mapped_data_dict[md.target_doctype] = {
            "r2_path": md.mapped_payload_r2_path,
            "total_rows": md.total_rows or 0
        }
        if md.validation_status == "failed":
            validation_status = "fail"

    # ── BUILD THE 3-PHASE IMPORT PLAN ─────────────────────────────────────────
    engine = _ImportEngine()
    plan = engine.build_plan(setup_steps, mapped_data_dict, validation_status)
    plan_status = plan.get("status", "blocked")

    slug = inp.company_slug or "unknown"
    plan_key = f"{slug}/{inp.project_id}/_import_plan/plan.json"
    
    final_plan_json = {
        "session_id": inp.session_id,
        "status": plan_status,
        "total_phases": plan.get("total_phases", 0),
        "total_steps": plan.get("total_steps", 0),
        "estimated_duration_minutes": plan.get("estimated_duration_minutes", 0),
        "phases": plan.get("phases", {})
    }

    try:
        s3 = _get_s3_client()
        s3.put_object(
            Bucket="clean-data",
            Key=plan_key,
            Body=json.dumps(final_plan_json, indent=2, default=str).encode("utf-8"),
            ContentType="application/json",
        )
    except Exception as e:
        activity.logger.error("  ❌ R2 plan upload failed: %s", e)

    plan_id = uuid.uuid4()
    if plan_status == "ready":
        try:
            async with AsyncSessionLocal() as db_session:
                db_session.add(ISImportPlan(
                    id=plan_id,
                    session_id=uuid.UUID(inp.session_id),
                    total_phases=plan.get("total_phases", 0),
                    total_steps=plan.get("total_steps", 0),
                    plan_r2_path=plan_key,
                    phases=plan.get("phases", {}),
                    status="ready",
                ))
                await db_session.commit()
        except Exception as e:
            activity.logger.error("  ❌ Supabase ISImportPlan insert failed: %s", e)

    try:
        from containers.implementation.file_io.persist_audit import log_audit
        await log_audit(
            session_id=inp.session_id,
            action="import_plan_created",
            actor="system",
            entity_type="import_plan",
            entity_id=str(plan_id),
            details={"status": plan_status, "phases": plan.get("total_phases"), "steps": plan.get("total_steps")},
            result="success",
        )
    except Exception:
        pass

    return plan_status


@activity.defn(name="execute_import_phase")
async def execute_import_phase(inp: ExecutePhaseInput) -> Dict[str, Any]:
    """
    Step 13: Execute (or dry-run) a single import phase by pushing data to ERPNext row by row.
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
        return {"phase": inp.phase_id, "status": "error", "error": "Import plan not found."}

    phases = import_plan.phases or {}
    phase_def = phases.get(inp.phase_id)
    if not phase_def:
        return {"phase": inp.phase_id, "status": "error", "error": f"Phase {inp.phase_id} not in plan."}

    steps = phase_def.get("steps", [])

    # Update plan status
    async with AsyncSessionLocal() as session:
        await session.execute(
            update(ISImportPlan)
            .where(ISImportPlan.id == import_plan.id)
            .values(status="executing", current_phase=inp.phase_id)
        )
        await session.commit()

    # ── 2. Execute Steps ─────────────────────────────────────────────────────
    s3 = _get_s3_client()
    slug = inp.company_slug or "unknown"
    
    execution_logs = []
    total_records_created = 0
    steps_completed = 0
    steps_failed = 0

    # Ensure clean Base URL — auto-resolve from Project.deployment_details if not provided
    base_url = (inp.erpnext_base_url or "").rstrip("/")
    api_token = inp.erpnext_api_key or ""
    verify_ssl = True
    allow_insecure_ssl = True

    # ── AUTO-RESOLVE: Fetch credentials from Project.deployment_details if missing ──
    if inp.project_id:
        try:
            from shared.models.core import Project
            async with AsyncSessionLocal() as db:
                stmt = select(Project).where(Project.id == uuid.UUID(inp.project_id))
                res = await db.execute(stmt)
                project = res.scalar_one_or_none()
                if project and project.deployment_details:
                    details = project.deployment_details
                    if not base_url:
                        base_url = (details.get("site_url", "") or "").rstrip("/")
                        activity.logger.info("  🔑 Auto-resolved base_url from Project.deployment_details: %s", base_url)
                    if not api_token:
                        dk = details.get("api_key", "")
                        ds = details.get("api_secret", "")
                        if dk and ds:
                            api_token = f"{dk}:{ds}"
                            activity.logger.info("  🔑 Auto-resolved API credentials from Project.deployment_details")
                        else:
                            activity.logger.warning("  ⚠️ Project.deployment_details has no api_key/api_secret")
                            
                    v_ssl = details.get("verify_ssl")
                    if v_ssl is not None:
                        verify_ssl = str(v_ssl).lower() not in ("false", "0", "no")
                    a_ssl = details.get("allow_insecure_ssl")
                    if a_ssl is not None:
                        allow_insecure_ssl = str(a_ssl).lower() not in ("false", "0", "no")
                else:
                    activity.logger.warning("  ⚠️ No Project or deployment_details found for project_id=%s", inp.project_id)
        except Exception as e:
            activity.logger.error("  ❌ Failed to auto-resolve credentials from Project: %s", e)

    headers = {
        "Authorization": f"token {api_token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    } if api_token else {}

    # Increase timeout for bulk ERPNext processing
    async with httpx.AsyncClient(base_url=base_url, timeout=60.0, verify=verify_ssl) as default_client:
        client = default_client
        unverified_client = None

        # ── PRE-FLIGHT SEEDER ─────────────────────────────────────────────────
        # Runs BEFORE the main import loop.
        # Seeds all `use_default` doctypes (UOM, Item Group, Territory, etc.)
        # using values from erpnext_deafaults_baseline.json so that link-
        # validation never fails when importing Items, Customers, etc.
        seed_steps = [s for s in steps if s.get("action") == "seed_from_baseline"]

        if seed_steps and not inp.dry_run and base_url:
            activity.logger.info("")
            activity.logger.info("  🌱  PRE-FLIGHT SEEDER — seeding %d baseline doctype(s)", len(seed_steps))

            baseline: Dict[str, List] = {}
            if _BASELINE_PATH.exists():
                with open(_BASELINE_PATH, "r", encoding="utf-8") as _bf:
                    baseline = json.load(_bf)
            else:
                activity.logger.warning("  ⚠️  Baseline file not found: %s", _BASELINE_PATH)

            for seed_step in seed_steps:
                dt_seed = seed_step["doctype"]
                baseline_values: List[str] = baseline.get(dt_seed, [])

                if not baseline_values:
                    activity.logger.warning("  ⚠️  No baseline values for %s — skipping seed", dt_seed)
                    continue

                seeded = 0
                already = 0
                failed  = 0

                for bval in baseline_values:
                    record = _build_baseline_record(dt_seed, bval)
                    try:
                        _resp = await client.post(
                            f"/api/resource/{dt_seed}",
                            json=record,
                            headers=headers,
                        )
                        if _resp.status_code in (409, 417):
                            # 409 = already exists, 417 = duplicate name — both are OK
                            already += 1
                        else:
                            _resp.raise_for_status()
                            seeded += 1
                    except Exception as _se:
                        # Non-fatal: log and continue — a missing seed value will
                        # surface as a link error on the specific row that uses it
                        err_text = str(_se)
                        if hasattr(_se, "response") and _se.response is not None:
                            try:
                                err_text = _se.response.json().get("exc_message", _se.response.text)
                            except Exception:
                                err_text = _se.response.text
                        # Tolerate "already exists" style errors from Frappe
                        if "already exist" in err_text.lower() or "duplicate" in err_text.lower():
                            already += 1
                        else:
                            failed += 1
                            activity.logger.warning("  ⚠️  Seed %s '%s' failed: %s", dt_seed, bval, err_text)

                activity.logger.info(
                    "  🌱  %-22s  seeded=%d  already_existed=%d  failed=%d",
                    dt_seed, seeded, already, failed
                )

        elif seed_steps and inp.dry_run:
            activity.logger.info("  🌱  PRE-FLIGHT SEEDER — dry_run mode, skipping %d seed step(s)", len(seed_steps))

        activity.logger.info("")
        # ── END PRE-FLIGHT SEEDER ─────────────────────────────────────────────

        for step_idx, step in enumerate(steps):
            dt = step.get("doctype", "")
            action = step.get("action", "")
            step_start = datetime.utcnow()

            # Skip actions that are not row-level imports
            if action in ("default_or_skip", "skip", "seed_from_baseline", "data_gap"):
                if action == "data_gap":
                    activity.logger.warning(
                        "  ⚠️  DATA GAP: %s has no mapped data file and no baseline — skipping", dt
                    )
                continue

            # Download payload from R2
            rows = []
            try:
                # data_source contains the R2 path we mapped in build_plan
                r2_key = step.get("data_source")
                response = s3.get_object(Bucket="clean-data", Key=r2_key)
                payload = json.loads(response["Body"].read().decode("utf-8"))
                rows = payload.get("records", [])
            except Exception as e:
                activity.logger.warning("  No R2 data found for %s — skipping", dt)
                continue

            records_attempted = len(rows)
            records_succeeded = 0
            records_failed = 0
            error_details = []
            erpnext_responses = []

            # Dry Run vs Live
            if inp.dry_run or not base_url:
                records_succeeded = records_attempted
                steps_completed += 1
                status = "success"
                erpnext_responses = ["DRY_RUN_MOCK_SUCCESS"] * records_succeeded
            else:
                # 🚀 LIVE IMPORT: Row-by-Row Frappe API Posting
                for row_idx, row in enumerate(rows):
                    try:
                        try:
                            # Frappe API wants {"customer_name": "ABC"}, NOT {"data": [...]}
                            resp = await client.post(
                                f"/api/resource/{dt}",
                                json=row,
                                headers=headers,
                            )
                        except Exception as client_exc:
                            if verify_ssl and allow_insecure_ssl and "CERTIFICATE_VERIFY_FAILED" in str(client_exc):
                                activity.logger.warning("  ⚠️ SSL verify failed, switching to unverified client for remaining rows")
                                if not unverified_client:
                                    unverified_client = httpx.AsyncClient(base_url=base_url, timeout=60.0, verify=False)
                                client = unverified_client
                                verify_ssl = False  # only switch once
                                resp = await client.post(
                                    f"/api/resource/{dt}",
                                    json=row,
                                    headers=headers,
                                )
                            else:
                                raise client_exc

                        resp.raise_for_status()
                        
                        records_succeeded += 1
                        
                        # Frappe returns the created document in 'data'
                        resp_data = resp.json()
                        erpnext_responses.append(resp_data.get("data", {}))
                        
                    except Exception as exc:
                        records_failed += 1
                        err_msg = str(exc)
                        if hasattr(exc, 'response') and exc.response is not None:
                            try:
                                # Try to grab Frappe's specific error message
                                err_msg = exc.response.json().get("exc_message", exc.response.text)
                            except Exception:
                                err_msg = exc.response.text
                                
                        error_details.append({"row_index": row_idx, "error": err_msg})
                        activity.logger.error("  ❌ ERPNext API Error on %s row %d: %s", dt, row_idx, err_msg)

                status = "failed" if records_failed > 0 else "success"
                if records_failed > 0:
                    steps_failed += 1
                else:
                    steps_completed += 1

            total_records_created += records_succeeded
            duration_sec = (datetime.utcnow() - step_start).total_seconds()

            # Build Log Object
            log_entry = {
                "step": step_idx + 1,
                "doctype": dt,
                "status": status,
                "records_attempted": records_attempted,
                "records_succeeded": records_succeeded,
                "records_failed": records_failed,
                "duration_seconds": int(duration_sec)
            }
            execution_logs.append(log_entry)

            # Persist to Supabase ISImportLog
            async with AsyncSessionLocal() as db_session:
                db_session.add(ISImportLog(
                    id=uuid.uuid4(),
                    import_plan_id=import_plan.id,
                    phase=inp.phase_id,
                    step_number=step_idx + 1,
                    doctype=dt,
                    action=action,
                    status=status,
                    records_attempted=records_attempted,
                    records_succeeded=records_succeeded,
                    records_failed=records_failed,
                    error_message="Import errors occurred" if records_failed > 0 else None,
                    error_details=json.dumps(error_details) if error_details else None,
                    erpnext_response=json.dumps(erpnext_responses[:5]) if erpnext_responses else None, # Save first 5 responses for auditing
                    started_at=step_start,
                    completed_at=datetime.utcnow(),
                    duration_seconds=int(duration_sec)
                ))
                await db_session.commit()

        if unverified_client:
            await unverified_client.aclose()

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
    phase_status = "error" if steps_failed > 0 else "success"
    try:
        from containers.implementation.file_io.persist_audit import log_audit
        await log_audit(
            session_id=inp.session_id,
            action="import_executed",
            actor="system",
            entity_type="import",
            details={
                "phase": inp.phase_id, 
                "steps_completed": steps_completed, 
                "records_created": total_records_created
            },
            result=phase_status,
        )
    except Exception:
        pass

    activity.logger.info("✅ execute_import_phase done | phase=%s records=%d", inp.phase_id, total_records_created)
    
    # ── 5. Return Output per Blueprint ───────────────────────────────────────
    return {
        "phase": inp.phase_id,
        "status": phase_status,
        "steps_completed": steps_completed,
        "steps_failed": steps_failed,
        "records_created": total_records_created,
        "execution_logs": execution_logs
    }