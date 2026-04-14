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
from typing import Any, Dict, List, Optional
from uuid import UUID

from temporalio.client import Client, WorkflowHandle
from temporalio.exceptions import WorkflowAlreadyStartedError
from sqlalchemy.future import select

from shared.database.db import AsyncSessionLocal
from shared.models.is_models import (
    ISSession, ISCompanyProfile, ISTargetStructure,
    ISMappedData, ISValidationResult, ISValidationError,
    ISImportPlan, ISImportLog,
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

    async def _handle(self, project_id: str | UUID) -> WorkflowHandle:
        client = await _get_client()
        return client.get_workflow_handle(_wf_id(project_id))

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def start(self, project_id: str | UUID) -> Dict[str, Any]:
        client = await _get_client()
        wf_id = _wf_id(project_id)
        
        discovery_meta = None
        async with AsyncSessionLocal() as session:
            stmt = select(Hook).where(Hook.project_id == UUID(str(project_id)))
            res = await session.execute(stmt)
            hook = res.scalar_one_or_none()
            if hook and hook.discovery_metadata:
                discovery_meta = hook.discovery_metadata

        try:
            handle = await client.start_workflow(
                ImplementationWorkflow.run,
                args=[str(project_id), discovery_meta],
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
    ) -> None:
        handle = await self._handle(project_id)
        await handle.signal(
            ImplementationWorkflow.files_uploaded,
            FilesUploadedSignal(uploaded_files=uploaded_files, company_slug=company_slug),
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
        handle = await self._handle(project_id)
        await handle.signal(
            ImplementationWorkflow.sandbox_approved,
            SandboxApprovedSignal(
                erpnext_base_url=erpnext_base_url,
                erpnext_api_key=erpnext_api_key,
                dry_run=dry_run,
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
        async with AsyncSessionLocal() as session:
            stmt = select(ISSession).where(ISSession.project_id == UUID(str(project_id)))
            res = await session.execute(stmt)
            return res.scalar_one_or_none()

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

    async def get_full_state(self, project_id: str | UUID) -> Dict[str, Any]:
        """Convenience: returns everything in one round-trip batch."""
        import asyncio
        h = await self._handle(project_id)
        stage, tasks = await asyncio.gather(
            h.query(ImplementationWorkflow.get_stage),
            h.query(ImplementationWorkflow.get_analysis_tasks),
        )
        return {
            "stage": stage, 
            "profile": await self.get_profile(project_id), 
            "analysis_tasks": tasks
        }