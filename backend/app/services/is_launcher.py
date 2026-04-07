"""
Implementation Launcher — connects the FastAPI layer to the Temporal IS workflow.

Queries now rely heavily on Supabase to fetch offloaded state.
No huge data transfers pass through Temporal history.
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
from shared.models.is_models import ISSession, ISMapping, ISImportRun

from containers.implementation.is_workflow.workflow import (
    ImplementationWorkflow,
    TASK_QUEUE,
    FilesUploadedSignal,
    F3icheConfirmedSignal,
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
        try:
            handle = await client.start_workflow(
                ImplementationWorkflow.run,
                str(project_id),
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

    # ── Supabase State Reading ────────────────────────────────────────────────

    async def _get_session(self, project_id: str | UUID) -> Optional[ISSession]:
        async with AsyncSessionLocal() as session:
            stmt = select(ISSession).where(ISSession.project_id == UUID(str(project_id)))
            res = await session.execute(stmt)
            return res.scalar_one_or_none()

    async def get_profile(self, project_id: str | UUID) -> Dict[str, Any]:
        is_session = await self._get_session(project_id)
        return is_session.f3iche_profile if is_session and is_session.f3iche_profile else {}

    async def get_validation_report(self, project_id: str | UUID) -> Optional[Dict]:
        is_session = await self._get_session(project_id)
        if not is_session:
            return None
        
        async with AsyncSessionLocal() as session:
            stmt = select(ISMapping).where(ISMapping.session_id == is_session.id)
            mappings = (await session.execute(stmt)).scalars().all()
            
            if not mappings:
                return None
                
            checks = []
            errors = []
            warnings = []
            overall = "pass"
            
            for m in mappings:
                if m.validation_report:
                    checks.append(m.validation_report)
                    errors.extend(m.validation_report.get("errors", []))
                    warnings.extend(m.validation_report.get("warnings", []))
                    if m.validation_report.get("status") == "fail":
                        overall = "fail"
                        
            return {
                "overall": overall,
                "checks": checks,
                "errors": errors,
                "warnings": warnings,
            }

    async def get_import_plan(self, project_id: str | UUID) -> Optional[Dict]:
        is_session = await self._get_session(project_id)
        if not is_session:
            return None
            
        async with AsyncSessionLocal() as session:
            stmt = select(ISImportRun).where(ISImportRun.session_id == is_session.id)
            runs = (await session.execute(stmt)).scalars().all()
            
            if not runs:
                return None
                
            phases = [run.execution_plan for run in runs if run.execution_plan]
            return {
                "status": "ready",
                "phases": phases,
                "total_steps": sum(len(p.get("steps", [])) for p in phases)
            }

    async def get_import_results(self, project_id: str | UUID) -> List[Dict]:
        is_session = await self._get_session(project_id)
        if not is_session:
            return []
            
        async with AsyncSessionLocal() as session:
            stmt = select(ISImportRun).where(ISImportRun.session_id == is_session.id)
            runs = (await session.execute(stmt)).scalars().all()
            return [run.results for run in runs if run.results]

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