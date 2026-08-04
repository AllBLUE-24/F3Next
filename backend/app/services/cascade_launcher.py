"""
backend/app/services/cascade_launcher.py

Temporal client wrapper for the Cascade (operations control plane) worker.
"""

from __future__ import annotations

import logging
import os
import uuid

from temporalio.client import Client
from temporalio.common import WorkflowIDReusePolicy

from containers.cascade.cascade_workflow.workflow import (
    CASCADE_QUEUE,
    CascadeEventInput,
    CascadeEventWorkflow,
)

logger = logging.getLogger(__name__)


class CascadeLauncher:
    """Start CascadeEventWorkflow runs from verified CVS webhooks."""

    async def _client(self) -> Client:
        return await Client.connect(os.getenv("TEMPORAL_HOST", "localhost:7233"))

    async def trigger_cascade_event(
        self,
        project_id: str,
        company_slug: str,
        webhook_payload: dict,
    ) -> dict:
        doctype = webhook_payload.get("doctype", "")
        doc_name = webhook_payload.get("name", "")
        trigger_event = (
            webhook_payload.get("event")
            or webhook_payload.get("trigger_event")
            or "on_submit"
        )

        workflow_id = f"cascade-wh-{project_id}-{doc_name or uuid.uuid4().hex[:8]}"
        client = await self._client()

        inp = CascadeEventInput(
            project_id=project_id,
            company_slug=company_slug,
            doctype=doctype,
            doc_name=doc_name,
            trigger_event=trigger_event,
            event_payload=webhook_payload,
        )

        try:
            await client.start_workflow(
                CascadeEventWorkflow.run,
                inp,
                id=workflow_id,
                task_queue=CASCADE_QUEUE,
                id_reuse_policy=WorkflowIDReusePolicy.ALLOW_DUPLICATE,
            )
            logger.info(
                "Cascade workflow started: doctype=%s doc=%s project=%s",
                doctype,
                doc_name,
                project_id,
            )
            try:
                from shared.cascade_metrics import CASCADE_EVENTS_RECEIVED_TOTAL

                if CASCADE_EVENTS_RECEIVED_TOTAL:
                    CASCADE_EVENTS_RECEIVED_TOTAL.labels(result="ok").inc()
            except Exception:
                pass
            return {"ok": True, "workflow_id": workflow_id}

        except Exception as e:
            logger.exception("Cascade workflow failed to start: %s", e)
            try:
                from shared.cascade_metrics import CASCADE_EVENTS_RECEIVED_TOTAL

                if CASCADE_EVENTS_RECEIVED_TOTAL:
                    CASCADE_EVENTS_RECEIVED_TOTAL.labels(result="fail").inc()
            except Exception:
                pass
            return {"ok": False, "error": str(e)}
