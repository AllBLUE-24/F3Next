"""
containers/cascade/cascade_workflow/workflow.py

CascadeEventWorkflow — reactive operations pipeline.

Triggered by ERPNext webhooks (fan-out from CVS webhook receiver).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any, Optional

from temporalio import workflow
from temporalio.common import RetryPolicy

CASCADE_QUEUE = "cascade-main-queue"

_RETRY_2 = RetryPolicy(
    maximum_attempts=2,
    initial_interval=timedelta(seconds=3),
    backoff_coefficient=2.0,
)

_NO_RETRY = RetryPolicy(maximum_attempts=1)


@dataclass
class CascadeEventInput:
    project_id: str
    company_slug: str
    doctype: str
    doc_name: Optional[str] = None
    trigger_event: Optional[str] = None
    event_payload: Optional[dict] = None


@dataclass
class CascadeEventOutput:
    success: bool
    event_id: Optional[str] = None
    notifications_sent: int = 0
    matched_rules: int = 0
    error: Optional[str] = None


@workflow.defn
class CascadeEventWorkflow:
    """
    Steps:
      1. log_cascade_event
      2. resolve_cascade_rules
      3. translate_event_to_messages (skip if no rules)
      4. resolve_recipients
      5. dispatch_notifications
      6. mark_cascade_processed
    """

    @workflow.run
    async def run(self, inp: CascadeEventInput) -> CascadeEventOutput:
        payload = inp.event_payload or {}
        trigger_event = inp.trigger_event or payload.get("event") or "on_submit"

        event_result: dict = await workflow.execute_activity(
            "log_cascade_event",
            args=[{
                "project_id": inp.project_id,
                "doctype": inp.doctype,
                "doc_name": inp.doc_name,
                "trigger_event": trigger_event,
                "event_payload": payload,
                "workflow_id": workflow.info().workflow_id,
            }],
            task_queue=CASCADE_QUEUE,
            start_to_close_timeout=timedelta(seconds=15),
            retry_policy=_RETRY_2,
        )

        event_id = event_result.get("event_id")

        rules_result: dict = await workflow.execute_activity(
            "resolve_cascade_rules",
            args=[{
                "doctype": inp.doctype,
                "doc_name": inp.doc_name,
                "trigger_event": trigger_event,
                "event_payload": payload,
            }],
            task_queue=CASCADE_QUEUE,
            start_to_close_timeout=timedelta(seconds=15),
            retry_policy=_NO_RETRY,
        )

        matched_rules = rules_result.get("matched_rules") or []
        if not matched_rules:
            await workflow.execute_activity(
                "mark_cascade_processed",
                args=[{
                    "event_id": event_id,
                    "matched_rule_ids": [],
                    "risk_tier": rules_result.get("risk_tier") or "low",
                }],
                task_queue=CASCADE_QUEUE,
                start_to_close_timeout=timedelta(seconds=15),
                retry_policy=_RETRY_2,
            )
            return CascadeEventOutput(
                success=True,
                event_id=event_id,
                notifications_sent=0,
                matched_rules=0,
            )

        translate_result: dict = await workflow.execute_activity(
            "translate_event_to_messages",
            args=[{
                "matched_rules": matched_rules,
                "template_context": rules_result.get("template_context") or {},
                "risk_tier": rules_result.get("risk_tier"),
            }],
            task_queue=CASCADE_QUEUE,
            start_to_close_timeout=timedelta(seconds=15),
            retry_policy=_NO_RETRY,
        )

        recipient_result: dict = await workflow.execute_activity(
            "resolve_recipients",
            args=[{
                "project_id": inp.project_id,
                "messages": translate_result.get("messages") or [],
                "doctype": inp.doctype,
                "doc_name": inp.doc_name,
                "trigger_event": trigger_event,
            }],
            task_queue=CASCADE_QUEUE,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=_RETRY_2,
        )

        dispatch_result: dict = await workflow.execute_activity(
            "dispatch_notifications",
            args=[{
                "project_id": inp.project_id,
                "cascade_event_id": event_id,
                "deliveries": recipient_result.get("deliveries") or [],
            }],
            task_queue=CASCADE_QUEUE,
            start_to_close_timeout=timedelta(seconds=60),
            retry_policy=_RETRY_2,
        )

        await workflow.execute_activity(
            "mark_cascade_processed",
            args=[{
                "event_id": event_id,
                "matched_rule_ids": rules_result.get("matched_rule_ids") or [],
                "risk_tier": rules_result.get("risk_tier") or "low",
            }],
            task_queue=CASCADE_QUEUE,
            start_to_close_timeout=timedelta(seconds=15),
            retry_policy=_RETRY_2,
        )

        return CascadeEventOutput(
            success=True,
            event_id=event_id,
            notifications_sent=int(dispatch_result.get("sent") or 0),
            matched_rules=len(matched_rules),
        )
