"""
containers/context_versioning/context_store/activities.py

Temporal activities for reading context from Supabase / R2.

Used by:
  - CVS workflow (internal): to check if a snapshot already exists
  - OS context_retrieval (external): reads the latest snapshot for a project

Activities:
  read_latest_snapshot          — read latest Supabase snapshot for a project+layer
  invalidate_session_cache      — clear stale company_context from all active os_sessions
  log_context_event             — write a ContextEvent row (for os_command optimistic log)
  register_frappe_webhooks      — auto-configure Frappe webhooks post-IS-deployment (Sprint 2)
  recover_stuck_events          — re-trigger Temporal for unprocessed context_events (Sprint 2)
  cvs_force_sync_for_project    — fire baseline CVS sync from IS workflow Step 13.5 (Sprint 2)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from temporalio import activity

logger = logging.getLogger(__name__)


@activity.defn(name="read_latest_snapshot")
async def read_latest_snapshot(data: dict) -> Optional[dict]:
    """
    Read the latest context snapshot for a project + layer from Supabase.

    Input:
      { "project_id": str, "layer": str }

    Returns:
      The snapshot data dict, or None if no snapshot exists yet.
    """
    project_id = data.get("project_id", "")
    layer      = data.get("layer", "master_data")

    activity.heartbeat(f"Reading {layer} snapshot")

    try:
        from shared.database.db import AsyncSessionLocal
        from shared.models.cvs_models import ContextSnapshot
        from sqlalchemy import select

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(ContextSnapshot)
                .where(
                    ContextSnapshot.project_id == project_id,
                    ContextSnapshot.layer      == layer,
                )
                .order_by(ContextSnapshot.version.desc())
                .limit(1)
            )
            row = result.scalars().first()

        if not row:
            logger.debug("CVS: no %s snapshot for project %s", layer, project_id)
            return None

        logger.debug(
            "CVS: read %s snapshot v%d for project %s",
            layer, row.version, project_id,
        )
        return row.data

    except Exception as e:
        logger.exception("CVS: read_latest_snapshot failed: %s", e)
        return None


@activity.defn(name="invalidate_session_cache")
async def invalidate_session_cache(data: dict) -> dict:
    """
    Force all active OS sessions for a project to refresh their company_context
    on next command by clearing the cached company_context (or setting fetched_at
    to a past time so the TTL check triggers a refresh).

    This is called after a CVS snapshot is written so the OS immediately picks
    up the new context on the user's next command.

    Input:
      { "project_id": str }

    Returns:
      { "sessions_cleared": int }
    """
    project_id = data.get("project_id", "")

    activity.heartbeat("Invalidating OS session cache")

    try:
        from shared.database.db import AsyncSessionLocal
        from shared.models.os_models import OSSession
        from sqlalchemy import select, update

        # Set fetched_at to epoch to force TTL expiry on next read
        EPOCH_ISO = "1970-01-01T00:00:00+00:00"

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(OSSession).where(
                    OSSession.project_id == project_id,
                    OSSession.status     == "active",
                )
            )
            sessions = result.scalars().all()

            count = 0
            for s in sessions:
                # Nullify company_context so it will be re-fetched on next command
                s.company_context = None
                count += 1

            await session.commit()

        logger.info("CVS: invalidated company_context for %d OS sessions (project=%s)", count, project_id)
        return {"sessions_cleared": count}

    except Exception as e:
        logger.exception("CVS: invalidate_session_cache failed: %s", e)
        return {"sessions_cleared": 0}


@activity.defn(name="log_context_event")
async def log_context_event(data: dict) -> dict:
    """
    Write a ContextEvent audit log entry.

    Called:
      1. By the CVS webhook handler — before processing starts
      2. By the OS workflow — after successful command execution (optimistic log)

    Input:
      {
        "project_id":   str,
        "event_type":   str,   # e.g. "os_command_success", "so_submitted"
        "event_payload": dict, # raw webhook or OS command summary
        "doctype":      str,   # optional
        "doc_name":     str,   # optional
        "workflow_id":  str,   # optional Temporal workflow ID
      }

    Returns:
      { "event_id": str }
    """
    project_id    = data.get("project_id", "")
    event_type    = data.get("event_type", "unknown")
    event_payload = data.get("event_payload", {})
    doctype       = data.get("doctype")
    doc_name      = data.get("doc_name")
    workflow_id   = data.get("workflow_id")

    activity.heartbeat("Logging context event")

    try:
        from shared.database.db import AsyncSessionLocal
        from shared.models.cvs_models import ContextEvent

        async with AsyncSessionLocal() as session:
            event = ContextEvent(
                project_id    = project_id,
                event_type    = event_type,
                event_payload = event_payload,
                doctype       = doctype,
                doc_name      = doc_name,
                workflow_id   = workflow_id,
            )
            session.add(event)
            await session.commit()
            await session.refresh(event)

        logger.info(
            "CVS: logged event type=%s doctype=%s doc=%s project=%s",
            event_type, doctype, doc_name, project_id,
        )
        return {"event_id": str(event.id)}

    except Exception as e:
        logger.exception("CVS: log_context_event failed: %s", e)
        return {"event_id": ""}


# ── Sprint 2: Frappe Webhook Registration ──────────────────────────────────────

# Doctypes that must push events to our CVS webhook endpoint.
# Ordered: master data first, then transactional.
_WEBHOOK_DOCTYPES = [
    # Master data — triggers master_data layer rebuild
    ("Item",         ["after_insert", "on_update"]),
    ("Customer",     ["after_insert", "on_update"]),
    ("Supplier",     ["after_insert", "on_update"]),
    ("Warehouse",    ["after_insert", "on_update"]),
    ("Cost Center",  ["after_insert", "on_update"]),
    ("Item Group",   ["after_insert", "on_update"]),
    ("Territory",    ["after_insert", "on_update"]),
    ("UOM",          ["after_insert", "on_update"]),
    # Transactional — triggers transaction_intel layer rebuild
    ("Sales Order",      ["on_submit", "on_cancel"]),
    ("Sales Invoice",    ["on_submit", "on_cancel"]),
    ("Purchase Order",   ["on_submit", "on_cancel"]),
    ("Payment Entry",    ["on_submit", "on_cancel"]),
    ("Delivery Note",    ["on_submit", "on_cancel"]),
    ("Purchase Receipt", ["on_submit", "on_cancel"]),
]

# Fields we include per doctype — keeps webhook payload small (no full document dump)
_WEBHOOK_FIELDS: dict[str, list[str]] = {
    "Item":         ["name", "item_name", "item_group", "stock_uom",
                     "weight_per_unit", "weight_uom", "disabled"],
    "Customer":     ["name", "customer_name", "customer_group", "disabled"],
    "Supplier":     ["name", "supplier_name", "supplier_group", "disabled"],
    "Warehouse":    ["name", "warehouse_name", "warehouse_type", "disabled"],
    "Cost Center":  ["name", "cost_center_name", "disabled"],
    "Item Group":   ["name", "is_group"],
    "Territory":    ["name", "is_group"],
    "UOM":          ["name"],
    # Transactional: include key header fields only
    "Sales Order":      ["name", "customer", "status", "grand_total",
                         "transaction_date", "delivery_date"],
    "Sales Invoice":    ["name", "customer", "status", "grand_total",
                         "outstanding_amount", "due_date"],
    "Purchase Order":   ["name", "supplier", "status", "grand_total",
                         "transaction_date", "schedule_date"],
    "Payment Entry":    ["name", "party_type", "party", "paid_amount",
                         "payment_type", "posting_date"],
    "Delivery Note":    ["name", "customer", "status", "posting_date"],
    "Purchase Receipt": ["name", "supplier", "status", "posting_date"],
}


@activity.defn(name="register_frappe_webhooks")
async def register_frappe_webhooks(data: dict) -> dict:
    """
    Auto-register CVS webhook configurations on a Frappe/ERPNext instance.

    Called by the IS workflow immediately after the baseline CVS force-sync
    so that all future document changes in ERPNext automatically push events
    to our /api/cvs/webhook/{project_id} endpoint.

    Input:
      {
        "project_id":     str,
        "erp_url":        str,    # e.g. https://client.f3next.in
        "api_key":        str,
        "api_secret":     str,
        "webhook_secret": str,    # HMAC secret; stored in deployment_details
      }

    Returns:
      {
        "registered":  int,   # number of webhooks successfully created
        "skipped":     int,   # already existed
        "failed":      int,   # creation errors
        "details":     list,
      }
    """
    project_id     = data["project_id"]
    erp_url        = data["erp_url"].rstrip("/")
    api_key        = data["api_key"]
    api_secret     = data["api_secret"]
    webhook_secret = data["webhook_secret"]

    import os
    backend_url    = os.getenv("PUBLIC_BACKEND_URL", "https://f3next.in").rstrip("/")

    target_url = f"{backend_url}/api/cvs/webhook/{project_id}"

    activity.heartbeat("Registering Frappe webhooks")

    import httpx

    headers = {
        "Authorization": f"token {api_key}:{api_secret}",
        "Content-Type":  "application/json",
    }

    registered = skipped = failed = 0
    details: list[dict] = []

    async with httpx.AsyncClient(verify=False, timeout=15.0) as client:
        for doctype, events in _WEBHOOK_DOCTYPES:
            for event in events:
                webhook_name = f"F3Next CVS — {doctype} {event}"
                activity.heartbeat(f"Registering: {webhook_name}")

                # Check if webhook already exists to avoid duplicates
                check_resp = await client.get(
                    f"{erp_url}/api/resource/Webhook",
                    headers=headers,
                    params={
                        "filters": str([
                            ["webhook_doctype", "=", doctype],
                            ["request_url",     "=", target_url],
                            ["webhook_docevent","=", event],
                        ]),
                        "fields": '["name"]',
                        "limit":  "1",
                    },
                )

                if check_resp.is_success:
                    existing = check_resp.json().get("data", [])
                    if existing:
                        logger.info("CVS webhooks: already exists — %s %s", doctype, event)
                        skipped += 1
                        details.append({"doctype": doctype, "event": event, "status": "skipped"})
                        continue

                # Build webhook data fields (which document fields to include in payload)
                field_list = _WEBHOOK_FIELDS.get(doctype, ["name"])
                webhook_data = [{"fieldname": f, "key": f} for f in field_list]
                # Always include doctype and name for routing
                if not any(d["key"] == "name" for d in webhook_data):
                    webhook_data.insert(0, {"fieldname": "name", "key": "name"})

                # Frappe also needs doctype injected — we add it as a condition header
                payload = {
                    "webhook_doctype":  doctype,
                    "webhook_docevent": event,
                    "request_url":      target_url,
                    "request_method":   "POST",
                    "request_structure": "Form URL-Encoded",
                    "enable_security":  1,
                    "webhook_secret":   webhook_secret,
                    "webhook_data":     webhook_data,
                    # Inject doctype into payload so our endpoint can route correctly
                    "webhook_json": f'{{"doctype": "{doctype}"}}',
                }

                create_resp = await client.post(
                    f"{erp_url}/api/resource/Webhook",
                    headers=headers,
                    json={"data": payload},
                )

                if create_resp.is_success:
                    registered += 1
                    logger.info("CVS webhooks: registered — %s %s", doctype, event)
                    details.append({"doctype": doctype, "event": event, "status": "registered"})
                else:
                    failed += 1
                    logger.error(
                        "CVS webhooks: FAILED to register %s %s — %d %s",
                        doctype, event, create_resp.status_code, create_resp.text[:200],
                    )
                    details.append({
                        "doctype": doctype, "event": event,
                        "status": "failed", "error": create_resp.text[:200],
                    })

    logger.info(
        "CVS webhooks: registration complete — registered=%d skipped=%d failed=%d",
        registered, skipped, failed,
    )
    return {
        "registered": registered,
        "skipped":    skipped,
        "failed":     failed,
        "details":    details,
    }


# ── Sprint 2: Recovery Cron for Stuck Events ──────────────────────────────────

@activity.defn(name="recover_stuck_events")
async def recover_stuck_events(data: dict) -> dict:
    """
    Drain context_events rows where processed_at IS NULL and received_at is
    older than `stale_minutes` ago. Re-triggers a CVSUpdateWorkflow for each.

    This is the safety net for events that landed in the DB (Step 4 of the
    webhook handler) but whose Temporal workflow never started or was dropped.

    Input:
      { "stale_minutes": int = 5 }   # default: events older than 5 minutes

    Returns:
      { "recovered": int, "errors": int }
    """
    stale_minutes = data.get("stale_minutes", 5)

    activity.heartbeat("Scanning for stuck context_events")

    try:
        from shared.database.db import AsyncSessionLocal
        from shared.models.cvs_models import ContextEvent
        from sqlalchemy import select, update
        from sqlalchemy.sql import func
        from datetime import timedelta
        import os

        from temporalio.client import Client
        from temporalio.common import WorkflowIDReusePolicy
        from containers.context_versioning.cvs_workflow.workflow import (
            CVSUpdateWorkflow, CVSUpdateInput,
        )
        from backend.app.api.cvs import _load_profile_for_project

        client = await Client.connect(os.getenv("TEMPORAL_HOST", "localhost:7233"))

        cutoff = datetime.now(timezone.utc) - timedelta(minutes=stale_minutes)

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(ContextEvent).where(
                    ContextEvent.processed_at == None,  # noqa: E711
                    ContextEvent.received_at  <= cutoff,
                )
                .order_by(ContextEvent.received_at)
                .limit(50)   # process max 50 per run to avoid thundering herd
            )
            stuck = result.scalars().all()

        if not stuck:
            logger.info("CVS recover: no stuck events found.")
            return {"recovered": 0, "errors": 0}

        logger.warning("CVS recover: found %d stuck event(s) — re-triggering", len(stuck))

        recovered = errors = 0

        for event in stuck:
            try:
                project_id = str(event.project_id)
                company_slug, company_profile = await _load_profile_for_project(project_id)

                from backend.app.services.cvs_launcher import _layers_for_doctype
                layers   = _layers_for_doctype(event.doctype or "")
                wf_id    = f"cvs-recover-{event.id}"

                inp = CVSUpdateInput(
                    project_id      = project_id,
                    company_slug    = company_slug,
                    company_profile = company_profile,
                    trigger_event   = "recovery",
                    trigger_doctype = event.doctype,
                    doc_name        = event.doc_name,
                    layers          = layers,
                    event_payload   = event.event_payload or {},
                )

                await client.start_workflow(
                    CVSUpdateWorkflow.run,
                    inp,
                    id                = wf_id,
                    task_queue        = "cvs-main-queue",
                    id_reuse_policy   = WorkflowIDReusePolicy.TERMINATE_IF_RUNNING,
                )

                recovered += 1
                logger.info("CVS recover: re-triggered workflow for event_id=%s", event.id)

            except Exception as e:
                errors += 1
                logger.error("CVS recover: failed to re-trigger event_id=%s: %s", event.id, e)

        logger.info("CVS recover: recovered=%d errors=%d", recovered, errors)
        return {"recovered": recovered, "errors": errors}

    except Exception as e:
        logger.exception("CVS recover: recover_stuck_events failed: %s", e)
        return {"recovered": 0, "errors": 1}



# -- Sprint 2: CVS Force-Sync Trigger (for IS workflow Step 13.5) ---------------

@activity.defn(name="cvs_force_sync_for_project")
async def cvs_force_sync_for_project(data: dict) -> dict:
    """
    Fire a baseline CVS force-sync for a project via the backend API.

    Called by IS workflow Step 13.5 immediately after all import phases
    complete, to seed Supabase CVS tables with live ERPNext data.

    Uses an internal HTTP call to /api/cvs/force-sync/{project_id} which
    starts a CVSWorkflow on the cvs-main-queue. This keeps the IS worker
    decoupled from the CVS worker's Temporal task queue.

    Input:
      {
        "project_id":   str,
        "company_slug": str,
      }

    Returns:
      { "ok": bool, "workflow_id": str }
    """
    project_id   = data["project_id"]
    company_slug = data.get("company_slug", "")
    
    import os
    backend_url  = os.getenv("BACKEND_INTERNAL_URL", "http://backend_api:8000").rstrip("/")

    activity.heartbeat("Triggering baseline CVS force-sync")

    import httpx

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                f"{backend_url}/api/cvs/force-sync/{project_id}",
                json={"company_slug": company_slug},
            )
            resp.raise_for_status()
            result = resp.json()

        logger.info(
            "CVS bootstrap: force-sync started for project=%s workflow_id=%s",
            project_id, result.get("workflow_id"),
        )
        return {
            "ok":          result.get("ok", True),
            "workflow_id": result.get("workflow_id", ""),
        }

    except Exception as e:
        logger.error("CVS bootstrap: force-sync trigger failed: %s", e)
        raise
