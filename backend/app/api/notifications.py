"""Notifications API — in-app ops center (Phase 6) + reply → OS (Phase 7)."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.services.os_launcher import dispatch_os_command
from shared.database.db import get_shared_db
from shared.models.command import CommandRequest, NotificationReplyRequest, NotificationReplyResponse
from shared.models.core import Project
from shared.models.notification_models import Notification

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notifications", tags=["Notifications"])


class MarkReadRequest(BaseModel):
    user_id: str


@router.get("/{project_id}")
async def list_notifications(
    project_id: UUID,
    user_id: str = Query(...),
    status: Optional[str] = Query(default=None),
    limit: int = Query(default=30, ge=1, le=100),
    db: AsyncSession = Depends(get_shared_db),
):
    """List notifications for the authenticated user in a project workspace."""
    query = (
        select(Notification)
        .where(
            Notification.project_id == project_id,
            Notification.recipient_client_id == user_id,
        )
        .order_by(Notification.created_at.desc())
        .limit(limit)
    )
    if status:
        query = query.where(Notification.status == status)

    rows = (await db.execute(query)).scalars().all()

    unread = sum(1 for n in rows if n.status in ("pending", "sent"))

    return {
        "notifications": [
            {
                "id": str(n.id),
                "title": n.title,
                "body": n.body,
                "department": n.department,
                "risk_tier": n.risk_tier,
                "status": n.status,
                "channel": n.channel,
                "payload": n.payload or {},
                "related_os_workflow_id": n.related_os_workflow_id,
                "created_at": n.created_at.isoformat() if n.created_at else None,
                "read_at": n.read_at.isoformat() if n.read_at else None,
            }
            for n in rows
        ],
        "unread_count": unread,
    }


@router.post("/{notification_id}/read")
async def mark_notification_read(
    notification_id: UUID,
    body: MarkReadRequest,
    db: AsyncSession = Depends(get_shared_db),
):
    result = await db.execute(
        select(Notification).where(Notification.id == notification_id)
    )
    notif = result.scalar_one_or_none()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    if notif.recipient_client_id != body.user_id:
        raise HTTPException(status_code=403, detail="Not your notification")

    notif.status = "read"
    notif.read_at = datetime.now(timezone.utc)
    await db.commit()

    return {"status": "read", "id": str(notification_id)}


@router.post("/{notification_id}/reply", response_model=NotificationReplyResponse)
async def reply_to_notification(
    notification_id: UUID,
    body: NotificationReplyRequest,
    db: AsyncSession = Depends(get_shared_db),
):
    """
    Reply to a cascade notification — routes into the existing OS command pipeline
    with seed_context from the triggering ERPNext document.
    """
    result = await db.execute(
        select(Notification).where(Notification.id == notification_id)
    )
    notif = result.scalar_one_or_none()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    if notif.recipient_client_id != body.user_id:
        raise HTTPException(status_code=403, detail="Not your notification")

    project_result = await db.execute(
        select(Project).where(Project.id == notif.project_id)
    )
    project = project_result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    seed_context = dict(notif.payload or {})
    seed_context.setdefault("doctype", seed_context.get("doctype"))
    seed_context.setdefault("doc_name", seed_context.get("doc_name"))
    seed_context["notification_id"] = str(notif.id)
    seed_context["notification_title"] = notif.title

    dispatch = await dispatch_os_command(
        CommandRequest(
            prompt=body.prompt.strip(),
            project_id=str(notif.project_id),
            company_id=body.company_id or project.company_slug or "",
            user_id=body.user_id,
            mode=body.mode,
            seed_context=seed_context,
            origin_notification_id=str(notif.id),
        )
    )

    await db.execute(
        update(Notification)
        .where(Notification.id == notification_id)
        .values(
            status="actioned",
            related_os_workflow_id=dispatch.workflow_id,
            read_at=datetime.now(timezone.utc),
        )
    )
    await db.commit()

    logger.info(
        "Notification reply dispatched: notif=%s workflow=%s",
        notification_id,
        dispatch.workflow_id,
    )

    return NotificationReplyResponse(
        workflow_id=dispatch.workflow_id,
        session_id=dispatch.session_id,
        notification_id=str(notification_id),
    )
