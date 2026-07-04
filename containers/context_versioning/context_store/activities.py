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
                update(OSSession)
                .where(
                    OSSession.project_id == project_id,
                    OSSession.status == "active",
                )
                .values(company_context=None)
                .returning(OSSession.id)
            )
            count = len(result.fetchall())
            await session.commit()

        logger.info("CVS: invalidated company_context for %d OS sessions (project=%s)", count, project_id)
        try:
            from shared.context_engine import get_context_engine

            await get_context_engine().invalidate_project(str(project_id))
        except Exception as ce:
            logger.warning("CVS: context engine invalidate failed: %s", ce)

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


# ── Snapshot retention (Option 3: latest version only in Supabase) ───────────

_SNAPSHOTS_PRUNE_PROJECT_SQL = """
DELETE FROM context_snapshots AS cs
USING context_snapshots AS newer
WHERE cs.project_id = :pid
  AND newer.project_id = :pid
  AND cs.layer = newer.layer
  AND cs.version < newer.version
"""


async def _connect_asyncpg():
    """asyncpg connection tuned for Supabase / PgBouncer (no prepared statement cache)."""
    import asyncpg

    from shared.database.db import DATABASE_URL

    sync_url = (DATABASE_URL or "").replace("postgresql+asyncpg://", "postgresql://")
    if not sync_url or "sqlite" in sync_url:
        raise RuntimeError("PostgreSQL DATABASE_URL required")
    return await asyncpg.connect(sync_url, statement_cache_size=0)


async def _prune_snapshots_global_swap(conn) -> int:
    """
    Keep latest row per (project_id, layer) via temp table + TRUNCATE.
    Fast for large tables; avoids NOT IN over hundreds of thousands of ids.
    """
    before = await conn.fetchval("SELECT COUNT(*)::bigint FROM context_snapshots")
    keep = await conn.fetchval(
        """
        SELECT COUNT(*)::bigint FROM (
            SELECT DISTINCT ON (project_id, layer) id
            FROM context_snapshots
            ORDER BY project_id, layer, version DESC
        ) t
        """
    )

    async with conn.transaction():
        await conn.execute("SET LOCAL statement_timeout = 0")
        await conn.execute(
            """
            CREATE TEMP TABLE cvs_snapshots_keep AS
            SELECT DISTINCT ON (project_id, layer) *
            FROM context_snapshots
            ORDER BY project_id, layer, version DESC
            """
        )
        await conn.execute("TRUNCATE context_snapshots")
        await conn.execute(
            """
            INSERT INTO context_snapshots (
                id, project_id, layer, version, data, trigger_event,
                trigger_doctype, r2_key, created_at
            )
            SELECT
                id, project_id, layer, version, data, trigger_event,
                trigger_doctype, r2_key, created_at
            FROM cvs_snapshots_keep
            """
        )

    deleted = int(before or 0) - int(keep or 0)
    return max(deleted, 0)


async def _prune_events_before(conn, cutoff, *, batch_size: int = 10000) -> int:
    """Delete old context_events in batches to stay under statement timeout."""
    await conn.execute("SET statement_timeout = 0")
    total = 0
    while True:
        status = await conn.execute(
            """
            DELETE FROM context_events
            WHERE id IN (
                SELECT id
                FROM context_events
                WHERE received_at < $1
                LIMIT $2
            )
            """,
            cutoff,
            batch_size,
        )
        try:
            n = int(status.split()[-1])
        except (ValueError, IndexError):
            n = 0
        if n <= 0:
            break
        total += n
    return total


async def prune_old_snapshots_core(data: dict | None = None) -> dict:
    """
    Retention policy for CVS telemetry tables (Foundation L0 baseline).

    - context_snapshots: keep only the latest version per (project_id, layer).
      Full history remains in R2 (see r2_key on the retained row).
    - context_events: delete rows older than CVS_EVENTS_RETENTION_DAYS (default 30).

    Optional input:
      project_id — scope snapshot pruning to one project (used after a successful write)
      events_retention_days — override env default
      vacuum — run VACUUM FULL on both tables (emergency / daily job only)
    """
    import os
    import uuid as _uuid

    from datetime import timedelta

    from sqlalchemy import text

    data = data or {}
    project_id = data.get("project_id")
    events_retention_days = int(
        data.get("events_retention_days")
        or os.getenv("CVS_EVENTS_RETENTION_DAYS", "30")
    )
    run_vacuum = bool(data.get("vacuum", False))
    use_global_swap = bool(data.get("global_swap", not project_id))

    snapshots_deleted = 0
    events_deleted = 0

    try:
        from shared.database.db import AsyncSessionLocal

        cutoff = datetime.now(timezone.utc) - timedelta(days=events_retention_days)

        if use_global_swap and not project_id:
            conn = await _connect_asyncpg()
            try:
                snapshots_deleted = await _prune_snapshots_global_swap(conn)
                events_deleted = await _prune_events_before(conn, cutoff)
            finally:
                await conn.close()
        else:
            async with AsyncSessionLocal() as session:
                if project_id:
                    pid = _uuid.UUID(str(project_id))
                    result = await session.execute(
                        text(_SNAPSHOTS_PRUNE_PROJECT_SQL),
                        {"pid": pid},
                    )
                    snapshots_deleted = result.rowcount or 0

                events_result = await session.execute(
                    text(
                        """
                        DELETE FROM context_events
                        WHERE id IN (
                            SELECT id FROM context_events
                            WHERE received_at < :cutoff
                            LIMIT 10000
                        )
                        """
                    ),
                    {"cutoff": cutoff},
                )
                events_deleted = events_result.rowcount or 0
                await session.commit()

        vacuum_ran = False
        if run_vacuum:
            vacuum_ran = await _vacuum_cvs_tables()

        logger.info(
            "CVS prune: snapshots_deleted=%d events_deleted=%d project=%s vacuum=%s",
            snapshots_deleted,
            events_deleted,
            project_id or "*",
            vacuum_ran,
        )
        return {
            "ok": True,
            "snapshots_deleted": snapshots_deleted,
            "events_deleted": events_deleted,
            "vacuum_ran": vacuum_ran,
        }

    except Exception as e:
        logger.exception("CVS prune_old_snapshots failed: %s", e)
        return {
            "ok": False,
            "snapshots_deleted": snapshots_deleted,
            "events_deleted": events_deleted,
            "error": str(e),
        }


async def _vacuum_cvs_tables() -> bool:
    """Run VACUUM FULL outside a transaction to reclaim disk on Supabase."""
    from shared.database.db import DATABASE_URL

    if not DATABASE_URL or "sqlite" in DATABASE_URL:
        logger.warning("CVS vacuum skipped — no PostgreSQL DATABASE_URL")
        return False

    try:
        conn = await _connect_asyncpg()
        try:
            await conn.execute("SET statement_timeout = 0")
            await conn.execute("VACUUM FULL context_snapshots")
            await conn.execute("VACUUM FULL context_events")
        finally:
            await conn.close()
        return True
    except Exception as e:
        logger.exception("CVS vacuum failed: %s", e)
        return False


@activity.defn(name="prune_old_snapshots")
async def prune_old_snapshots(data: dict) -> dict:
    """
    Temporal activity wrapper for prune_old_snapshots_core.

    Input:
      { "project_id": str (optional), "events_retention_days": int (optional) }
    """
    activity.heartbeat("Pruning old CVS snapshots and events")
    return await prune_old_snapshots_core(data)


@activity.defn(name="mark_event_processed")
async def mark_event_processed(data: dict) -> dict:
    """
    Set processed_at + version_produced on the ContextEvent row created in step 1.

    Input: { "event_id": str, "max_version": int | None }
    """
    import uuid as _uuid

    from sqlalchemy import update
    from sqlalchemy.sql import func as sqlfunc

    event_id = (data or {}).get("event_id") or ""
    max_version = (data or {}).get("max_version")
    if not event_id:
        return {"ok": True, "skipped": True}

    activity.heartbeat("mark_event_processed")

    try:
        from shared.database.db import AsyncSessionLocal
        from shared.models.cvs_models import ContextEvent

        vid = _uuid.UUID(str(event_id))
        ver = int(max_version) if max_version is not None else None

        async with AsyncSessionLocal() as session:
            await session.execute(
                update(ContextEvent)
                .where(ContextEvent.id == vid)
                .values(
                    processed_at=sqlfunc.now(),
                    version_produced=ver,
                )
            )
            await session.commit()

        logger.info("CVS: marked event processed id=%s version=%s", event_id, ver)
        return {"ok": True, "event_id": event_id}

    except Exception as e:
        logger.exception("CVS: mark_event_processed failed: %s", e)
        return {"ok": False, "error": str(e)}


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

    NOW USES ERPAdapter for ERP-agnostic webhook registration.

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
        "skipped":     int,   # already existed (detected inside adapter)
        "failed":      int,   # creation errors
        "details":     list,
      }
    """
    project_id     = data["project_id"]
    webhook_secret = data["webhook_secret"]

    import os
    from shared.erp_adapters.registry import get_adapter

    backend_url = os.getenv("PUBLIC_BACKEND_URL", "https://f3next.in").rstrip("/")
    target_url = f"{backend_url}/api/cvs/webhook/{project_id}"

    activity.heartbeat("Registering Frappe webhooks via ERPAdapter")

    # Build profile for adapter
    profile = {
        "erp_type":           "erpnext",
        "erp_url":            data["erp_url"].rstrip("/"),
        "api_key":            data["api_key"],
        "api_secret":         data["api_secret"],
        "verify_ssl":         False,  # typically dev/test environments
        "allow_insecure_ssl": True,
    }

    adapter = get_adapter(profile)

    registered = 0
    skipped = 0
    failed = 0
    details: list[dict] = []

    for doctype, events in _WEBHOOK_DOCTYPES:
        for event in events:
            activity.heartbeat(f"Registering: {doctype} {event}")

            field_list = _WEBHOOK_FIELDS.get(doctype, ["name"])

            success = await adapter.register_webhook(
                doctype=doctype,
                event=event,
                callback_url=target_url,
                webhook_secret=webhook_secret,
                field_list=field_list,
            )

            if success:
                # Adapter returns True for both "created" and "already exists"
                # We log both as success but don't distinguish here
                registered += 1
                details.append({"doctype": doctype, "event": event, "status": "registered"})
            else:
                failed += 1
                details.append({
                    "doctype": doctype,
                    "event": event,
                    "status": "failed",
                    "error": "Adapter returned False — check logs",
                })

    logger.info(
        "CVS webhooks: registration complete — registered=%d failed=%d",
        registered, failed,
    )
    return {
        "registered": registered,
        "skipped":    skipped,  # adapter doesn't distinguish, so always 0 here
        "failed":     failed,
        "details":    details,
    }


# ── Sprint 2: Recovery Cron for Stuck Events ──────────────────────────────────

async def recover_stuck_events_core(data: dict) -> dict:
    """
    Core implementation for stuck-event recovery (callable from cron script or activity).
    """
    stale_minutes = data.get("stale_minutes", 5)

    try:
        from datetime import timedelta
        import os

        from sqlalchemy import select
        from temporalio.client import Client
        from temporalio.common import WorkflowIDReusePolicy

        from containers.context_versioning.cvs_workflow.workflow import (
            CVSUpdateInput,
            CVSUpdateWorkflow,
        )
        from shared.cvs_profile import load_cvs_company_profile
        from shared.database.db import AsyncSessionLocal
        from shared.models.cvs_models import ContextEvent

        client = await Client.connect(os.getenv("TEMPORAL_HOST", "localhost:7233"))

        cutoff = datetime.now(timezone.utc) - timedelta(minutes=stale_minutes)

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(ContextEvent)
                .where(
                    ContextEvent.processed_at == None,  # noqa: E711
                    ContextEvent.received_at <= cutoff,
                )
                .order_by(ContextEvent.received_at)
                .limit(50)
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
                company_slug, company_profile = await load_cvs_company_profile(project_id)

                from shared.cvs_routing import layers_for_doctype

                layers = layers_for_doctype(event.doctype or "")

                inp = CVSUpdateInput(
                    project_id=project_id,
                    company_slug=company_slug,
                    company_profile=company_profile,
                    trigger_event="recovery",
                    trigger_doctype=event.doctype,
                    doc_name=event.doc_name,
                    layers=layers,
                    event_payload=event.event_payload or {},
                )

                await client.start_workflow(
                    CVSUpdateWorkflow.run,
                    inp,
                    id=f"cvs-recover-{event.id}",
                    task_queue="cvs-main-queue",
                    id_reuse_policy=WorkflowIDReusePolicy.TERMINATE_IF_RUNNING,
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


@activity.defn(name="recover_stuck_events")
async def recover_stuck_events(data: dict) -> dict:
    """
    Drain context_events rows where processed_at IS NULL and received_at is
    older than `stale_minutes` ago. Re-triggers a CVSUpdateWorkflow for each.

    Input:
      { "stale_minutes": int = 5 }

    Returns:
      { "recovered": int, "errors": int }
    """
    activity.heartbeat("Scanning for stuck context_events")
    return await recover_stuck_events_core(data)



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
    project_id = data["project_id"]

    import os

    from shared.cvs_profile import build_force_sync_company_profile

    slug, company_profile = await build_force_sync_company_profile(project_id)
    company_slug = data.get("company_slug") or slug

    backend_url = os.getenv("BACKEND_INTERNAL_URL", "http://backend_api:8000").rstrip("/")

    activity.heartbeat("Triggering baseline CVS force-sync")

    import httpx

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                f"{backend_url}/api/cvs/force-sync/{project_id}",
                json={
                    "company_slug": company_slug,
                    "company_profile": company_profile,
                },
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
