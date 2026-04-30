"""
containers/context_versioning/context_store/activities.py

Temporal activities for reading context from Supabase / R2.

Used by:
  - CVS workflow (internal): to check if a snapshot already exists
  - OS context_retrieval (external): reads the latest snapshot for a project

Activities:
  read_latest_snapshot     — read latest Supabase snapshot for a project+layer
  invalidate_session_cache — clear stale company_context from all active os_sessions
  log_context_event        — write a ContextEvent row (for os_command optimistic log)
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
