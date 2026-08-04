"""Resolve notification recipients by department."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from temporalio import activity

from shared.database.db import AsyncSessionLocal
from shared.models.core import Project, ProjectMember


@activity.defn(name="resolve_recipients")
async def resolve_recipients(data: dict[str, Any]) -> dict[str, Any]:
    """
    Map department-scoped messages to client_ids.

    Fallback: workspace owner when no member has the target department.
    """
    project_id = uuid.UUID(str(data["project_id"]))
    messages = data.get("messages") or []

    async with AsyncSessionLocal() as session:
        project = (
            await session.execute(select(Project).where(Project.id == project_id))
        ).scalar_one_or_none()
        if not project:
            return {"deliveries": [], "error": "project not found"}

        members = (
            await session.execute(
                select(ProjectMember).where(ProjectMember.project_id == project_id)
            )
        ).scalars().all()

        by_department: dict[str, list[str]] = {}
        for member in members:
            if member.department:
                by_department.setdefault(member.department, []).append(member.client_id)

        owner_id = project.client_id
        deliveries: list[dict[str, Any]] = []

        for msg in messages:
            dept = msg.get("department")
            recipient_ids = list(by_department.get(dept or "", []))
            if not recipient_ids:
                recipient_ids = [owner_id]
                fallback = True
            else:
                fallback = False

            for client_id in recipient_ids:
                deliveries.append({
                    "recipient_client_id": client_id,
                    "department": dept,
                    "title": msg.get("title"),
                    "body": msg.get("body"),
                    "risk_tier": msg.get("risk_tier") or "low",
                    "rule_id": msg.get("rule_id"),
                    "owner_fallback": fallback,
                    "payload": {
                        "doctype": data.get("doctype"),
                        "doc_name": data.get("doc_name"),
                        "trigger_event": data.get("trigger_event"),
                        "rule_id": msg.get("rule_id"),
                    },
                })

    activity.logger.info(
        "Cascade recipients: project=%s deliveries=%d",
        project_id,
        len(deliveries),
    )
    return {"deliveries": deliveries, "count": len(deliveries)}
