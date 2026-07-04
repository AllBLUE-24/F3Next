"""
containers/context_versioning/cvs_workflow/workflow.py

The CVS Update Workflow — orchestrates a full context snapshot rebuild.

Triggered by:
  1. POST /api/cvs/force-sync/{company_id}  — IS pipeline calls this after deployment
  2. POST /api/cvs/webhook/{company_id}     — ERPNext webhook arrives (Phase 2)
  3. OS optimistic event log                — after a successful OS command

One workflow execution = one context update event, end-to-end.

Workflow ID strategy:
  force_sync:  cvs-force-{project_id}           (replaces any running sync)
  webhook:     cvs-wh-{project_id}-{doc_name}    (one per webhook event)
  os_command:  cvs-os-{project_id}-{command_id}  (one per OS success)
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any, Optional

from temporalio import workflow
from temporalio.common import RetryPolicy

logger = logging.getLogger(__name__)

# ── Retry policies ─────────────────────────────────────────────────────────────

_RETRY_2 = RetryPolicy(
    maximum_attempts    = 2,
    initial_interval    = timedelta(seconds=3),
    backoff_coefficient = 2.0,
)

_RETRY_3 = RetryPolicy(
    maximum_attempts    = 3,
    initial_interval    = timedelta(seconds=5),
    backoff_coefficient = 2.0,
)

_NO_RETRY = RetryPolicy(maximum_attempts=1)

CVS_QUEUE = "cvs-main-queue"


# ── Input/Output types ─────────────────────────────────────────────────────────

from dataclasses import dataclass, field


@dataclass
class CVSUpdateInput:
    project_id:      str
    company_slug:    str
    company_profile: dict            # identity layer — contains ERP credentials
    trigger_event:   str             # force_sync / webhook / os_command
    layers:          list            # which layers to rebuild
    trigger_doctype: Optional[str] = None
    doc_name:        Optional[str]  = None
    event_payload:   Optional[dict] = None


@dataclass
class CVSUpdateOutput:
    success:       bool
    versions:      dict
    r2_keys:       dict
    layers_built:  list
    error:         Optional[str] = None


# ── Workflow ───────────────────────────────────────────────────────────────────

@workflow.defn
class CVSUpdateWorkflow:
    """
    Context Versioning Service — Update Workflow.

    Steps:
      1. Log the incoming context event (audit trail)
      2. Fetch fresh data from ERPNext + write to Supabase + R2
      2b. Mark the context event as processed
      2c. Prune historical Supabase snapshot rows (R2 retains full history)
      3. Invalidate OS session caches so the next command picks up new context
    """

    @workflow.run
    async def run(self, inp: CVSUpdateInput) -> CVSUpdateOutput:
        _HR = "─" * 56

        workflow.logger.info(
            "\n%s\n🔄  CVS UPDATE — trigger=%s  layers=%s  project=%s\n%s",
            _HR, inp.trigger_event, inp.layers, inp.project_id, _HR,
        )

        # ── Step 1: Log the event ─────────────────────────────────────────────
        event_result: dict = await workflow.execute_activity(
            "log_context_event",
            args=[{
                "project_id":    inp.project_id,
                "event_type":    inp.trigger_event,
                "event_payload": inp.event_payload or {},
                "doctype":       inp.trigger_doctype,
                "doc_name":      inp.doc_name,
                "workflow_id":   workflow.info().workflow_id,
            }],
            task_queue             = CVS_QUEUE,
            start_to_close_timeout = timedelta(seconds=15),
            retry_policy           = _RETRY_2,
        )

        workflow.logger.info(
            "✅ CVS [1] event logged: id=%s", event_result.get("event_id", "?")
        )

        # ── Step 2: Build + store snapshot ────────────────────────────────────
        snapshot_result: dict = await workflow.execute_activity(
            "build_and_store_snapshot",
            args=[{
                "project_id":      inp.project_id,
                "company_slug":    inp.company_slug,
                "company_profile": inp.company_profile,
                "layers":          inp.layers,
                "trigger_event":   inp.trigger_event,
                "trigger_doctype": inp.trigger_doctype,
            }],
            task_queue             = CVS_QUEUE,
            start_to_close_timeout = timedelta(seconds=120),  # ERPNext can be slow
            retry_policy           = _RETRY_3,
        )

        if not snapshot_result.get("success"):
            workflow.logger.error("CVS: snapshot build failed for project=%s", inp.project_id)
            return CVSUpdateOutput(
                success      = False,
                versions     = {},
                r2_keys      = {},
                layers_built = [],
                error        = "Snapshot build failed — check ERPNext connectivity",
            )

        workflow.logger.info(
            "✅ CVS [2] snapshot built: layers=%s versions=%s",
            snapshot_result.get("layers_built"),
            snapshot_result.get("versions"),
        )

        # ── Step 2b: Mark audit event processed ─────────────────────────────────
        await workflow.execute_activity(
            "mark_event_processed",
            args=[{
                "event_id":    event_result.get("event_id", ""),
                "max_version": snapshot_result.get("max_version"),
            }],
            task_queue             = CVS_QUEUE,
            start_to_close_timeout = timedelta(seconds=15),
            retry_policy           = _RETRY_2,
        )

        workflow.logger.info(
            "✅ CVS [2b] event marked processed id=%s", event_result.get("event_id", "?")
        )

        # ── Step 2c: Prune historical Supabase rows (R2 retains full history) ─
        prune_result: dict = await workflow.execute_activity(
            "prune_old_snapshots",
            args=[{"project_id": inp.project_id}],
            task_queue             = CVS_QUEUE,
            start_to_close_timeout = timedelta(seconds=60),
            retry_policy           = _NO_RETRY,
        )

        workflow.logger.info(
            "✅ CVS [2c] pruned stale rows: snapshots=%d events=%d",
            prune_result.get("snapshots_deleted", 0),
            prune_result.get("events_deleted", 0),
        )

        # ── Step 3: Invalidate OS session caches ──────────────────────────────
        cache_result: dict = await workflow.execute_activity(
            "invalidate_session_cache",
            args=[{"project_id": inp.project_id}],
            task_queue             = CVS_QUEUE,
            start_to_close_timeout = timedelta(seconds=15),
            retry_policy           = _RETRY_2,
        )

        workflow.logger.info(
            "✅ CVS [3] OS sessions invalidated: count=%d\n%s\n🏁  CVS UPDATE COMPLETE\n%s",
            cache_result.get("sessions_cleared", 0), _HR, _HR,
        )

        return CVSUpdateOutput(
            success      = True,
            versions     = snapshot_result.get("versions", {}),
            r2_keys      = snapshot_result.get("r2_keys", {}),
            layers_built = snapshot_result.get("layers_built", []),
        )
