"""
backend/app/services/cvs_launcher.py

Temporal client wrapper for the Context Versioning Service.
Mirrors the pattern of ImplementationLauncher and OSLauncher.

Used by:
  backend/app/api/cvs.py (the FastAPI routes)

Responsibilities:
  - Start CVSUpdateWorkflow runs
  - Route force-sync, webhook, and os_command triggers
  - Read latest context snapshot from Supabase for the OS
"""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from temporalio.client import Client, WorkflowExecutionStatus
from temporalio.common import WorkflowIDReusePolicy

from containers.context_versioning.cvs_workflow.workflow import (
    CVSUpdateWorkflow,
    CVSUpdateInput,
)
from shared.cvs_routing import layers_for_doctype as _layers_for_doctype

logger = logging.getLogger(__name__)

CVS_QUEUE = "cvs-main-queue"


class CVSLauncher:
    """Thin async wrapper over the Temporal client for CVS workflows."""

    async def _client(self) -> Client:
        return await Client.connect(os.getenv("TEMPORAL_HOST", "localhost:7233"))

    # ── Force sync (called by IS pipeline after deployment) ───────────────────

    async def force_sync(
        self,
        project_id:      str,
        company_slug:    str,
        company_profile: dict,
        layers: Optional[list] = None,
    ) -> dict:
        """
        Trigger a full context sync for a company.

        Uses WorkflowIDReusePolicy.TERMINATE_IF_RUNNING so if a sync is already
        in progress for this company, it is cancelled and restarted with fresh data.

        Called by:
          - POST /api/cvs/force-sync/{company_id}  (IS pipeline after deployment)
          - POST /api/cvs/force-sync/{company_id}  (admin manual trigger)
        """
        if layers is None:
            layers = ["master_data", "transaction_intel"]

        workflow_id = f"cvs-force-{project_id}"
        client      = await self._client()

        inp = CVSUpdateInput(
            project_id      = project_id,
            company_slug    = company_slug,
            company_profile = company_profile,
            trigger_event   = "force_sync",
            layers          = layers,
        )

        try:
            handle = await client.start_workflow(
                CVSUpdateWorkflow.run,
                inp,
                id                    = workflow_id,
                task_queue            = CVS_QUEUE,
                id_reuse_policy       = WorkflowIDReusePolicy.TERMINATE_IF_RUNNING,
            )
            logger.info("CVS force-sync started: workflow_id=%s project=%s", workflow_id, project_id)
            return {"ok": True, "workflow_id": workflow_id}

        except Exception as e:
            logger.exception("CVS force-sync failed to start: %s", e)
            return {"ok": False, "error": str(e)}

    # ── Webhook trigger (Phase 2 — wired in when webhooks arrive) ─────────────

    async def trigger_webhook_sync(
        self,
        project_id:      str,
        company_slug:    str,
        company_profile: dict,
        webhook_payload: dict,
    ) -> dict:
        """
        Trigger a targeted context sync from an ERPNext webhook event.

        Determines which layers to rebuild based on the incoming doctype.
        """
        doctype  = webhook_payload.get("doctype", "")
        doc_name = webhook_payload.get("name", "")

        layers = _layers_for_doctype(doctype)

        workflow_id = f"cvs-wh-{project_id}-{doc_name or uuid.uuid4().hex[:8]}"
        client      = await self._client()

        inp = CVSUpdateInput(
            project_id      = project_id,
            company_slug    = company_slug,
            company_profile = company_profile,
            trigger_event   = "webhook",
            trigger_doctype = doctype,
            doc_name        = doc_name,
            layers          = layers,
            event_payload   = webhook_payload,
        )

        try:
            await client.start_workflow(
                CVSUpdateWorkflow.run,
                inp,
                id                    = workflow_id,
                task_queue            = CVS_QUEUE,
                id_reuse_policy       = WorkflowIDReusePolicy.ALLOW_DUPLICATE,
            )
            logger.info(
                "CVS webhook sync started: doctype=%s doc=%s project=%s",
                doctype, doc_name, project_id,
            )
            return {"ok": True, "workflow_id": workflow_id, "layers": layers}

        except Exception as e:
            logger.exception("CVS webhook sync failed to start: %s", e)
            return {"ok": False, "error": str(e)}

    # ── OS command trigger (optimistic event log after successful OS command) ──

    async def trigger_os_command_sync(
        self,
        project_id:      str,
        company_slug:    str,
        company_profile: dict,
        command_summary: dict,  # {doctype, doc_name, intent_id}
    ) -> dict:
        """
        Trigger a targeted context sync after a successful OS command.

        This is the "optimistic" path — the OS workflow calls this directly
        after execution succeeds. The webhook from ERPNext will also arrive
        ~5s later, but this gives the OS context an immediate nudge.
        """
        doctype  = command_summary.get("doctype", "")
        doc_name = command_summary.get("doc_name", "")
        layers   = _layers_for_doctype(doctype)

        workflow_id = f"cvs-os-{project_id}-{doc_name or uuid.uuid4().hex[:8]}"
        client      = await self._client()

        inp = CVSUpdateInput(
            project_id      = project_id,
            company_slug    = company_slug,
            company_profile = company_profile,
            trigger_event   = "os_command",
            trigger_doctype = doctype,
            doc_name        = doc_name,
            layers          = layers,
            event_payload   = command_summary,
        )

        try:
            await client.start_workflow(
                CVSUpdateWorkflow.run,
                inp,
                id                    = workflow_id,
                task_queue            = CVS_QUEUE,
                id_reuse_policy       = WorkflowIDReusePolicy.ALLOW_DUPLICATE,
            )
            logger.info(
                "CVS OS-command sync started: doctype=%s doc=%s project=%s",
                doctype, doc_name, project_id,
            )
            return {"ok": True, "workflow_id": workflow_id}

        except Exception as e:
            logger.exception("CVS OS-command sync failed to start: %s", e)
            return {"ok": False, "error": str(e)}

    # ── Read latest context (used by OS context_retrieval) ────────────────────

    async def get_latest_context(
        self,
        project_id: str,
        layer: str = "master_data",
    ) -> Optional[dict]:
        """
        Read the latest context snapshot from Supabase for a given project + layer.

        Used directly by the FastAPI /api/cvs/context/{company_id} endpoint,
        and also by the OS context_retrieval module.

        Returns None if no snapshot exists yet (IS not yet complete).
        """
        try:
            from shared.database.db import AsyncSessionLocal
            from shared.models.cvs_models import ContextSnapshot
            from sqlalchemy import select
            import uuid as uuid_lib

            pid = uuid_lib.UUID(str(project_id))

            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(ContextSnapshot)
                    .where(
                        ContextSnapshot.project_id == pid,
                        ContextSnapshot.layer      == layer,
                    )
                    .order_by(ContextSnapshot.version.desc())
                    .limit(1)
                )
                row = result.scalars().first()

            if not row:
                return None

            return {
                "layer":         row.layer,
                "version":       row.version,
                "data":          row.data,
                "r2_key":        row.r2_key,
                "trigger_event": row.trigger_event,
                "created_at":    row.created_at.isoformat() if row.created_at else None,
            }

        except Exception as e:
            logger.exception("CVS: get_latest_context failed: %s", e)
            return None
