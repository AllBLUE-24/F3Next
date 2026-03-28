"""
Implementation Launcher — connects the FastAPI layer to the Temporal IS workflow.

Responsibilities:
  • Start a new ImplementationWorkflow for a project
  • Send signals (file upload, F3iche confirm, mapped data, validation, sandbox approval)
  • Query workflow state (stage, profile, tasks, plan, results)
  • Return typed response dicts; never exposes Temporal handles to callers
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

# Signal / input types from the workflow
from containers.implementation.is_workflow.workflow import (
    ImplementationWorkflow,
    TASK_QUEUE,
    FilesUploadedSignal,
    F3icheConfirmedSignal,
    FilesMappedSignal,
    ValidationSubmittedSignal,
    SandboxApprovedSignal,
)

logger = logging.getLogger(__name__)

TEMPORAL_HOST = os.getenv("TEMPORAL_HOST")
_client: Optional[Client] = None

def _wf_id(project_id: str | UUID) -> str:
    return f"impl-{project_id}"

async def _get_client() -> Client:
    """Return a cached Temporal client. Created once per process."""
    global _client
    if _client is None:
        host = os.getenv("TEMPORAL_HOST", TEMPORAL_HOST)
        _client = await Client.connect(host)
        logger.info("Temporal client connected to %s", host)
    return _client


class ImplementationLauncher:
    """
    Stateless helper — instantiate once per request (or inject as a singleton).
    Now manages its own Temporal connection like os_launcher.py.
    """

    def __init__(self):
        # We no longer need to pass the client in here
        pass

    async def _handle(self, project_id: str | UUID) -> WorkflowHandle:
        client = await _get_client() # Fetch the client asynchronously
        return client.get_workflow_handle(
            _wf_id(project_id),
            workflow=ImplementationWorkflow,
        )

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def start(self, project_id: str | UUID) -> Dict[str, Any]:
        """
        Start a new ImplementationWorkflow.
        Safe to call multiple times — returns existing run if already started.
        """
        client = await _get_client() # Fetch the client here too
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
        """Terminate a running workflow (e.g. user aborts setup)."""
        await self._handle(project_id).terminate(reason=reason)

    # ── Signals ───────────────────────────────────────────────────────────────

    async def signal_files_uploaded(
        self,
        project_id: str | UUID,
        uploaded_files: List[Dict],
        file_contents: Optional[Dict[str, str]] = None,
    ) -> None:
        await self._handle(project_id).signal(
            ImplementationWorkflow.files_uploaded,
            FilesUploadedSignal(uploaded_files=uploaded_files, file_contents=file_contents),
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
        await self._handle(project_id).signal(
            ImplementationWorkflow.f3iche_confirmed,
            F3icheConfirmedSignal(
                f3iche_user=f3iche_user,
                industry=industry,
                industry_sub=industry_sub,
                company_name=company_name,
                company_size=company_size,
            ),
        )

    async def signal_files_mapped(
        self,
        project_id: str | UUID,
        mapped_data: Dict[str, Any],
    ) -> None:
        await self._handle(project_id).signal(
            ImplementationWorkflow.files_mapped,
            FilesMappedSignal(mapped_data=mapped_data),
        )

    async def signal_validation_submitted(
        self,
        project_id: str | UUID,
        responses: Dict[str, Any],
        profile_edits: Optional[Dict[str, Any]] = None,
        note: Optional[str] = None,
    ) -> None:
        await self._handle(project_id).signal(
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
        await self._handle(project_id).signal(
            ImplementationWorkflow.sandbox_approved,
            SandboxApprovedSignal(
                erpnext_base_url=erpnext_base_url,
                erpnext_api_key=erpnext_api_key,
                dry_run=dry_run,
            ),
        )

    # ── Queries ───────────────────────────────────────────────────────────────

    async def get_stage(self, project_id: str | UUID) -> str:
        return await self._handle(project_id).query(ImplementationWorkflow.get_stage)

    async def get_profile(self, project_id: str | UUID) -> Dict[str, Any]:
        return await self._handle(project_id).query(ImplementationWorkflow.get_profile)

    async def get_analysis_tasks(self, project_id: str | UUID) -> List[Dict]:
        return await self._handle(project_id).query(ImplementationWorkflow.get_analysis_tasks)

    async def get_validation_report(self, project_id: str | UUID) -> Optional[Dict]:
        return await self._handle(project_id).query(ImplementationWorkflow.get_validation_report)

    async def get_import_plan(self, project_id: str | UUID) -> Optional[Dict]:
        return await self._handle(project_id).query(ImplementationWorkflow.get_import_plan)

    async def get_import_results(self, project_id: str | UUID) -> List[Dict]:
        return await self._handle(project_id).query(ImplementationWorkflow.get_import_results)

    async def get_full_state(self, project_id: str | UUID) -> Dict[str, Any]:
        """Convenience: returns everything in one round-trip batch."""
        h = self._handle(project_id)
        stage, profile, tasks = await asyncio.gather(
            h.query(ImplementationWorkflow.get_stage),
            h.query(ImplementationWorkflow.get_profile),
            h.query(ImplementationWorkflow.get_analysis_tasks),
        )
        return {"stage": stage, "profile": profile, "analysis_tasks": tasks}


import asyncio  # noqa: E402 — intentional late import (only used in get_full_state)