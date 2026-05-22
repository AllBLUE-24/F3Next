"""
Implementation Launcher — connects the FastAPI layer to the Temporal IS workflow.

v2: Queries from normalised tables (ISCompanyProfile, ISValidationResult,
    ISImportPlan, ISImportLog) instead of old ISMapping/ISImportRun.
"""
from __future__ import annotations
import os
from dotenv import load_dotenv
load_dotenv()

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from temporalio.client import Client, WorkflowHandle
from temporalio.exceptions import WorkflowAlreadyStartedError
from sqlalchemy import select, update

from shared.database.db import AsyncSessionLocal
from shared.models.is_models import (
    ISSession, ISCompanyProfile, ISTargetStructure, ISDataReadinessAssessment,
    ISMappedData, ISValidationResult, ISValidationError,
    ISImportPlan, ISImportLog, ISSupervisorPrompt,
)
from shared.models.hooks import Hook

from containers.implementation.is_workflow.workflow import (
    ImplementationWorkflow,
    TASK_QUEUE,
    FilesUploadedSignal,
    F3icheConfirmedSignal,
    MappingConfirmedSignal,
    ValidationSubmittedSignal,
    SandboxApprovedSignal,
    SupervisorResponseSignal,
)

logger = logging.getLogger(__name__)

TEMPORAL_HOST = os.getenv("TEMPORAL_HOST")
_client: Optional[Client] = None

def _wf_id(project_id: str | UUID) -> str:
    return f"impl-{project_id}"

async def _get_client() -> Client:
    global _client
    if _client is None:
        host = os.getenv("TEMPORAL_HOST", TEMPORAL_HOST)
        _client = await Client.connect(host)
        logger.info("Temporal client connected to %s", host)
    return _client


class ImplementationLauncher:
    def __init__(self):
        pass

    async def _resolve_project_id(self, input_id: str | UUID) -> UUID:
        """
        Accepts either a project_id or a session_id.
        Queries the database to check if input_id is a session_id.
        If yes, returns the corresponding project_id.
        Otherwise, returns the input_id as a UUID.
        """
        try:
            val_uuid = UUID(str(input_id))
        except ValueError:
            return input_id

        async with AsyncSessionLocal() as session:
            # Check if there is a session with this ID
            stmt = select(ISSession).where(ISSession.id == val_uuid)
            res = await session.execute(stmt)
            is_session = res.scalar_one_or_none()
            if is_session:
                return is_session.project_id
            
            # If not a session ID, assume it is a project ID
            return val_uuid

    async def _handle(self, project_id: str | UUID) -> WorkflowHandle:
        resolved_project_id = await self._resolve_project_id(project_id)
        client = await _get_client()
        return client.get_workflow_handle(_wf_id(resolved_project_id))

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def start(self, project_id: str | UUID) -> Dict[str, Any]:
        resolved_project_id = await self._resolve_project_id(project_id)
        client = await _get_client()
        wf_id = _wf_id(resolved_project_id)
        
        discovery_meta = None
        async with AsyncSessionLocal() as session:
            stmt = select(Hook).where(Hook.project_id == UUID(str(resolved_project_id)))
            res = await session.execute(stmt)
            hook = res.scalar_one_or_none()
            if hook and hook.discovery_metadata:
                discovery_meta = hook.discovery_metadata

        try:
            handle = await client.start_workflow(
                ImplementationWorkflow.run,
                args=[str(resolved_project_id), discovery_meta],
                id=wf_id,
                task_queue=TASK_QUEUE,
            )
            return {"workflow_id": wf_id, "run_id": handle.first_execution_run_id, "started": True}
        except WorkflowAlreadyStartedError:
            return {"workflow_id": wf_id, "started": False, "detail": "Workflow already running"}

    async def terminate(self, project_id: str | UUID, reason: str = "cancelled") -> None:
        handle = await self._handle(project_id)
        await handle.terminate(reason=reason)

    # ── Signals ───────────────────────────────────────────────────────────────

    async def signal_files_uploaded(
        self,
        project_id: str | UUID,
        uploaded_files: List[Dict],
        company_slug: Optional[str] = None,
        user_note: Optional[str] = None,
    ) -> None:
        is_session = await self._get_session(project_id)
        if is_session:
            file_batches = list(is_session.file_batches or [])
            batch_index = len(file_batches) + 1
            file_batches.append({
                "batch_index": batch_index,
                "uploaded_at": datetime.utcnow().isoformat() + "Z",
                "files": uploaded_files,
                "note": user_note or "",
            })

            user_notes = list(is_session.user_notes or [])
            if user_note:
                user_notes.append({
                    "type": "initial_upload",
                    "batch_index": batch_index,
                    "note": user_note,
                    "uploaded_at": datetime.utcnow().isoformat() + "Z",
                })

            async with AsyncSessionLocal() as session:
                await session.execute(
                    update(ISSession)
                    .where(ISSession.id == is_session.id)
                    .values(
                        file_batches=file_batches,
                        user_notes=user_notes,
                        user_import_note=user_note or is_session.user_import_note,
                        updated_at=datetime.utcnow(),
                    )
                )
                await session.commit()

        handle = await self._handle(project_id)
        await handle.signal(
            ImplementationWorkflow.files_uploaded,
            FilesUploadedSignal(
                uploaded_files=uploaded_files,
                company_slug=company_slug,
                user_note=user_note,
            ),
        )

    async def signal_f3iche_confirmed(
        self,
        project_id: str | UUID,
        f3iche_user: str,
        industry: str,
        industry_sub: Optional[str] = None,
        company_name: Optional[str] = None,
        company_size: Optional[str] = None,
    ) -> None:
        handle = await self._handle(project_id)
        await handle.signal(
            ImplementationWorkflow.f3iche_confirmed,
            F3icheConfirmedSignal(
                f3iche_user=f3iche_user,
                industry=industry,
                industry_sub=industry_sub,
                company_name=company_name,
                company_size=company_size,
            ),
        )

    async def signal_mapping_confirmed(
        self,
        project_id: str | UUID,
        user_feedback: Optional[str] = None,
        approved: bool = False,
    ) -> None:
        handle = await self._handle(project_id)
        await handle.signal(
            ImplementationWorkflow.mapping_confirmed,
            MappingConfirmedSignal(
                user_feedback=user_feedback,
                approved=approved,
            ),
        )

    async def signal_validation_submitted(
        self,
        project_id: str | UUID,
        responses: Dict[str, Any],
        profile_edits: Optional[Dict[str, Any]] = None,
        note: Optional[str] = None,
    ) -> None:
        handle = await self._handle(project_id)
        await handle.signal(
            ImplementationWorkflow.validation_submitted,
            ValidationSubmittedSignal(
                responses=responses,
                profile_edits=profile_edits or {},
                note=note,
            ),
        )

    async def signal_sandbox_approved(
        self,
        project_id: str | UUID,
        erpnext_base_url: str,
        erpnext_api_key: str,
        dry_run: bool = False,
    ) -> None:
        from temporalio.service import RPCError
        handle = await self._handle(project_id)
        try:
            await handle.signal(
                ImplementationWorkflow.sandbox_approved,
                SandboxApprovedSignal(
                    erpnext_base_url=erpnext_base_url,
                    erpnext_api_key=erpnext_api_key,
                    dry_run=dry_run,
                ),
            )
        except RPCError as e:
            logger.warning(f"Failed to signal sandbox approved (likely completed/failed): {e}")

    async def signal_supervisor_response(
        self,
        project_id: str | UUID,
        prompt_id: str,
        chosen_action_id: str,
        extra_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        handle = await self._handle(project_id)
        await handle.signal(
            ImplementationWorkflow.supervisor_response,
            SupervisorResponseSignal(
                prompt_id=prompt_id,
                chosen_action_id=chosen_action_id,
                extra_data=extra_data or {},
            ),
        )

    # ── Queries ───────────────────────────────────────────────────────────────

    async def get_stage(self, project_id: str | UUID) -> str:
        handle = await self._handle(project_id)
        return await handle.query(ImplementationWorkflow.get_stage)

    async def get_analysis_tasks(self, project_id: str | UUID) -> List[Dict]:
        handle = await self._handle(project_id)
        return await handle.query(ImplementationWorkflow.get_analysis_tasks)

    # ── Supabase State Reading (v2 schema) ────────────────────────────────────

    async def _get_session(self, project_id: str | UUID) -> Optional[ISSession]:
        resolved_project_id = await self._resolve_project_id(project_id)
        async with AsyncSessionLocal() as session:
            stmt = (
                select(ISSession)
                .where(ISSession.project_id == UUID(str(resolved_project_id)))
                .order_by(ISSession.created_at.desc())
                .limit(1)
            )
            res = await session.execute(stmt)
            return res.scalars().first()

    async def get_profile(self, project_id: str | UUID) -> Dict[str, Any]:
        """Query latest ISCompanyProfile for this project."""
        is_session = await self._get_session(project_id)
        if not is_session:
            return {}
        
        async with AsyncSessionLocal() as session:
            stmt = (
                select(ISCompanyProfile)
                .where(ISCompanyProfile.session_id == is_session.id)
                .order_by(ISCompanyProfile.version.desc())
                .limit(1)
            )
            result = await session.execute(stmt)
            profile = result.scalar_one_or_none()
            
            if not profile:
                return {}
            
            return {
                "version": profile.version,
                "f3iche": profile.f3iche,
                "industry": profile.industry,
                "industry_sub": profile.industry_sub,
                "company_name": profile.company_name,
                "company_size": profile.company_size,
                "workflows": profile.workflows,
                "modules": profile.required_modules,
                "required_doctypes": profile.required_doctypes,
                "business_reality": profile.business_reality,
                "context_flags": profile.context_flags,
                "data_quality_score": profile.data_quality_score,
                "llm_confidence": profile.llm_confidence,
                "r2_path": profile.r2_path,
            }

    async def get_validation_report(self, project_id: str | UUID) -> Optional[Dict]:
        """Query ISValidationResult + ISValidationError for this project."""
        is_session = await self._get_session(project_id)
        if not is_session:
            return None
        
        async with AsyncSessionLocal() as session:
            stmt = select(ISValidationResult).where(ISValidationResult.session_id == is_session.id)
            results = (await session.execute(stmt)).scalars().all()
            
            if not results:
                return None
                
            checks = []
            all_errors = []
            all_warnings = []
            overall = "pass"
            
            for vr in results:
                # Get errors for this result
                err_stmt = select(ISValidationError).where(ISValidationError.validation_result_id == vr.id)
                errors = (await session.execute(err_stmt)).scalars().all()
                
                check_errors = [e.error_message for e in errors if e.severity == "error"]
                check_warnings = [e.error_message for e in errors if e.severity == "warning"]
                
                checks.append({
                    "doctype": vr.doctype,
                    "status": vr.overall_status,
                    "errors": check_errors,
                    "warnings": check_warnings,
                    "row_count": vr.row_count or 0,
                })
                all_errors.extend(check_errors)
                all_warnings.extend(check_warnings)
                if vr.overall_status == "fail":
                    overall = "fail"
                    
            return {
                "overall": overall,
                "checks": checks,
                "errors": all_errors,
                "warnings": all_warnings,
            }

    async def get_data_readiness(self, project_id: str | UUID) -> Optional[Dict[str, Any]]:
        """Query ISDataReadinessAssessment for this project."""
        is_session = await self._get_session(project_id)
        if not is_session:
            return None

        async with AsyncSessionLocal() as session:
            stmt = (
                select(ISDataReadinessAssessment)
                .where(ISDataReadinessAssessment.session_id == is_session.id)
                .order_by(ISDataReadinessAssessment.created_at.desc())
                .limit(1)
            )
            row = (await session.execute(stmt)).scalar_one_or_none()
            if not row:
                return None

            return {
                "ready_doctypes": row.ready_doctypes or [],
                "partial_doctypes": row.partial_doctypes or [],
                "missing_doctypes": row.missing_doctypes or [],
                "unmappable_chunks": row.unmappable_chunks or [],
                "gap_report": row.gap_report or {},
                "minimum_viable_possible": row.minimum_viable_possible,
                "user_action_required": row.user_action_required,
                "questions_for_user": row.questions_for_user or [],
                "import_readiness_score": row.import_readiness_score,
                "executive_summary": row.executive_summary,
                "user_decision": row.user_decision,
            }

    async def get_supervisor_prompts(self, project_id: str | UUID, status: str = "open") -> List[Dict[str, Any]]:
        """
        Return Supervisor prompts for the latest IS session of this project.
        """
        is_session = await self._get_session(project_id)
        if not is_session:
            return []

        async with AsyncSessionLocal() as session:
            stmt = (
                select(ISSupervisorPrompt)
                .where(ISSupervisorPrompt.session_id == is_session.id)
                .where(ISSupervisorPrompt.status == status)
                .order_by(ISSupervisorPrompt.created_at.desc())
                .limit(50)
            )
            rows = (await session.execute(stmt)).scalars().all()
            out: List[Dict[str, Any]] = []
            for r in rows:
                out.append(
                    {
                        "id": str(r.id),
                        "session_id": str(r.session_id),
                        "step": r.step,
                        "status": r.status,
                        "summary_for_ui": r.summary_for_ui,
                        "actions": r.actions or [],
                        "node_status": r.node_status or {},
                        "created_at": r.created_at.isoformat() if r.created_at else None,
                    }
                )
            return out

    async def answer_supervisor_prompt(
        self,
        project_id: str | UUID,
        prompt_id: str,
        chosen_action_id: str,
        extra_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Persist the user's answer and signal the workflow.
        """
        is_session = await self._get_session(project_id)
        if not is_session:
            raise ValueError("Implementation session not found")

        answer_payload = {"chosen_action_id": chosen_action_id, "extra_data": extra_data or {}}
        user_note = (extra_data or {}).get("user_note")

        from sqlalchemy import update

        async with AsyncSessionLocal() as session:
            stmt = select(ISSession).where(ISSession.id == is_session.id)
            row = (await session.execute(stmt)).scalar_one_or_none()
            await session.execute(
                update(ISSupervisorPrompt)
                .where(ISSupervisorPrompt.id == UUID(prompt_id))
                .values(status="answered", answer_payload=answer_payload)
            )

            if user_note:
                if row:
                    notes = list(row.user_notes or [])
                    notes.append({
                        "type": "supervisor_prompt",
                        "prompt_id": prompt_id,
                        "chosen_action_id": chosen_action_id,
                        "note": user_note,
                        "answered_at": datetime.utcnow().isoformat() + "Z",
                    })
                    await session.execute(
                        update(ISSession)
                        .where(ISSession.id == is_session.id)
                        .values(user_notes=notes, updated_at=datetime.utcnow())
                    )
            await session.commit()

        await self.signal_supervisor_response(project_id, prompt_id, chosen_action_id, extra_data=extra_data)

    async def get_import_plan(self, project_id: str | UUID) -> Optional[Dict]:
        """Query ISImportPlan for this project."""
        is_session = await self._get_session(project_id)
        if not is_session:
            return None
            
        async with AsyncSessionLocal() as session:
            stmt = (
                select(ISImportPlan)
                .where(ISImportPlan.session_id == is_session.id)
                .order_by(ISImportPlan.created_at.desc())
                .limit(1)
            )
            result = await session.execute(stmt)
            plan = result.scalar_one_or_none()
            
            if not plan:
                return None
                
            return {
                "status": plan.status,
                "phases": plan.phases or [],
                "total_steps": plan.total_steps or 0,
                "current_phase": plan.current_phase,
            }

    async def get_import_results(self, project_id: str | UUID) -> List[Dict]:
        """Query ISImportLog entries for this project."""
        is_session = await self._get_session(project_id)
        if not is_session:
            return []
            
        async with AsyncSessionLocal() as session:
            # Get the plan first
            plan_stmt = (
                select(ISImportPlan)
                .where(ISImportPlan.session_id == is_session.id)
                .order_by(ISImportPlan.created_at.desc())
                .limit(1)
            )
            plan = (await session.execute(plan_stmt)).scalar_one_or_none()
            if not plan:
                return []
            
            # Get all logs for this plan
            log_stmt = (
                select(ISImportLog)
                .where(ISImportLog.import_plan_id == plan.id)
                .order_by(ISImportLog.phase, ISImportLog.step_number)
            )
            logs = (await session.execute(log_stmt)).scalars().all()
            
            return [{
                "phase": log.phase,
                "step_number": log.step_number,
                "doctype": log.doctype,
                "action": log.action,
                "status": log.status,
                "records_attempted": log.records_attempted,
                "records_succeeded": log.records_succeeded,
                "records_failed": log.records_failed,
                "error_message": log.error_message,
            } for log in logs]

    async def get_validate_preview(self, project_id: str | UUID) -> Dict[str, Any]:
        """
        Fetch ALL mapped data payloads from R2 along with profile and validation results.
        Returns the complete dataset that will be imported — for user review.
        """
        import json
        import boto3
        from botocore.config import Config

        is_session = await self._get_session(project_id)
        if not is_session:
            return {"error": "No implementation session found"}

        # 1. Company profile
        profile = await self.get_profile(project_id)

        # 2. All mapped data rows
        async with AsyncSessionLocal() as session:
            mapped_stmt = (
                select(ISMappedData)
                .where(ISMappedData.session_id == is_session.id)
                .order_by(ISMappedData.target_doctype)
            )
            mapped_rows = (await session.execute(mapped_stmt)).scalars().all()

            # 3. Validation results + errors per doctype
            val_stmt = select(ISValidationResult).where(
                ISValidationResult.session_id == is_session.id
            )
            val_rows = (await session.execute(val_stmt)).scalars().all()

            val_map: Dict[str, Dict] = {}
            for vr in val_rows:
                err_stmt = select(ISValidationError).where(
                    ISValidationError.validation_result_id == vr.id
                )
                errors = (await session.execute(err_stmt)).scalars().all()
                val_map[vr.doctype] = {
                    "status": vr.overall_status,
                    "row_count": vr.row_count or 0,
                    "errors": [
                        {"message": e.error_message, "severity": e.severity, "field": e.field_name}
                        for e in errors
                    ],
                }

            # 4. Import plan (target structure phases)
            target_stmt = (
                select(ISTargetStructure)
                .where(ISTargetStructure.session_id == is_session.id)
                .order_by(ISTargetStructure.created_at.desc())
                .limit(1)
            )
            target_row = (await session.execute(target_stmt)).scalar_one_or_none()

        # 5. Download actual payloads from R2
        s3 = boto3.client(
            "s3",
            endpoint_url=os.getenv("R2_ENDPOINT"),
            aws_access_key_id=os.getenv("R2_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("R2_SECRET_ACCESS_KEY"),
            config=Config(signature_version="s3v4"),
            region_name="auto",
        )

        doctypes = []
        for md in mapped_rows:
            records = []
            columns = []
            r2_path = md.mapped_payload_r2_path

            if r2_path:
                try:
                    resp = s3.get_object(Bucket="clean-data", Key=r2_path)
                    payload = json.loads(resp["Body"].read().decode("utf-8"))
                    records = payload.get("records", [])
                    if records:
                        columns = list(records[0].keys())
                except Exception as e:
                    logger.warning("Failed to fetch R2 payload %s: %s", r2_path, e)

            validation = val_map.get(md.target_doctype, {
                "status": "pending", "row_count": 0, "errors": []
            })

            doctypes.append({
                "doctype": md.target_doctype,
                "source_file": md.source_filename,
                "total_rows": md.total_rows or len(records),
                "total_mapped_fields": md.total_mapped_fields or len(columns),
                "validation_status": validation["status"],
                "errors": [e for e in validation["errors"] if e["severity"] == "error"],
                "warnings": [e for e in validation["errors"] if e["severity"] == "warning"],
                "columns": columns,
                "records": records,
            })

        # 6. Import summary from target structure
        import_summary = {}
        if target_row:
            try:
                phases_raw = target_row.import_phases
                phases = json.loads(phases_raw) if isinstance(phases_raw, str) else (phases_raw or {})
                for phase_key, phase_val in phases.items():
                    if isinstance(phase_val, dict):
                        import_summary[phase_key] = phase_val.get("doctypes", [])
                    elif isinstance(phase_val, list):
                        import_summary[phase_key] = phase_val
            except Exception:
                pass

        validation_overall = "pass"
        for dt in doctypes:
            if dt["validation_status"] == "fail":
                validation_overall = "fail"
                break

        return {
            "profile": profile,
            "doctypes": doctypes,
            "import_summary": import_summary,
            "validation_overall": validation_overall,
        }

    async def get_full_state(self, project_id: str | UUID) -> Dict[str, Any]:
        """Convenience: returns everything in one round-trip batch."""
        import asyncio
        h = await self._handle(project_id)
        stage, tasks = await asyncio.gather(
            h.query(ImplementationWorkflow.get_stage),
            h.query(ImplementationWorkflow.get_analysis_tasks),
        )
        session = await self._get_session(project_id)
        file_batches = list(session.file_batches or []) if session else []
        total_files = sum(len((batch or {}).get("files") or []) for batch in file_batches)
        return {
            "stage": stage, 
            "profile": await self.get_profile(project_id), 
            "analysis_tasks": tasks,
            "session": {
                "status": session.status if session else None,
                "user_import_note": session.user_import_note if session else None,
                "file_batches": file_batches,
                "user_notes": list(session.user_notes or []) if session else [],
                "total_files": total_files,
                "batch_count": len(file_batches),
                "completed_at": session.completed_at.isoformat() if session and session.completed_at else None,
                "updated_at": session.updated_at.isoformat() if session and session.updated_at else None,
            } if session else None,
        }