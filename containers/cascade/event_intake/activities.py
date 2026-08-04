"""Cascade event intake activities."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import update
from temporalio import activity

from shared.database.db import AsyncSessionLocal
from shared.models.notification_models import CascadeEvent


@activity.defn(name="log_cascade_event")
async def log_cascade_event(data: dict[str, Any]) -> dict[str, Any]:
    """Persist incoming ERPNext webhook as a cascade_events row."""
    event_id = uuid.uuid4()
    project_id = uuid.UUID(str(data["project_id"]))

    async with AsyncSessionLocal() as session:
        row = CascadeEvent(
            id=event_id,
            project_id=project_id,
            doctype=data.get("doctype") or "",
            doc_name=data.get("doc_name"),
            trigger_event=data.get("trigger_event") or "unknown",
            event_payload=data.get("event_payload") or {},
            matched_rule_ids=[],
            risk_tier=data.get("risk_tier") or "low",
            workflow_id=data.get("workflow_id"),
        )
        session.add(row)
        await session.commit()

    activity.logger.info(
        "Cascade event logged: id=%s doctype=%s doc=%s",
        event_id,
        data.get("doctype"),
        data.get("doc_name"),
    )
    return {"event_id": str(event_id), "success": True}


@activity.defn(name="mark_cascade_processed")
async def mark_cascade_processed(data: dict[str, Any]) -> dict[str, Any]:
    """Mark cascade event processed with matched rules."""
    event_id = data.get("event_id")
    if not event_id:
        return {"success": False, "error": "missing event_id"}

    async with AsyncSessionLocal() as session:
        await session.execute(
            update(CascadeEvent)
            .where(CascadeEvent.id == uuid.UUID(str(event_id)))
            .values(
                matched_rule_ids=data.get("matched_rule_ids") or [],
                risk_tier=data.get("risk_tier") or "low",
                processed_at=datetime.now(timezone.utc),
            )
        )
        await session.commit()

    return {"success": True, "event_id": event_id}
