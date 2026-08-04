"""Dispatch notifications via configured channels."""

from __future__ import annotations

from typing import Any

from temporalio import activity

from shared.notification_channels.in_app import InAppChannel


@activity.defn(name="dispatch_notifications")
async def dispatch_notifications(data: dict[str, Any]) -> dict[str, Any]:
    """Write one in-app notification per delivery."""
    deliveries = data.get("deliveries") or []
    project_id = data["project_id"]
    cascade_event_id = data.get("cascade_event_id")
    channel = InAppChannel()

    sent = 0
    failed = 0
    notification_ids: list[str] = []

    for delivery in deliveries:
        result = await channel.send(
            project_id=project_id,
            recipient_client_id=delivery["recipient_client_id"],
            department=delivery.get("department"),
            title=delivery.get("title") or "ERPNext update",
            body=delivery.get("body") or "",
            payload=delivery.get("payload") or {},
            risk_tier=delivery.get("risk_tier") or "low",
            cascade_event_id=cascade_event_id,
        )
        if result.ok:
            sent += 1
            if result.notification_id:
                notification_ids.append(result.notification_id)
            try:
                from shared.cascade_metrics import CASCADE_NOTIFICATIONS_DISPATCHED_TOTAL

                if CASCADE_NOTIFICATIONS_DISPATCHED_TOTAL:
                    CASCADE_NOTIFICATIONS_DISPATCHED_TOTAL.labels(
                        channel=result.channel,
                        department=delivery.get("department") or "unknown",
                    ).inc()
            except Exception:
                pass
        else:
            failed += 1
            activity.logger.warning(
                "Notification dispatch failed: %s", result.error
            )

    activity.logger.info(
        "Cascade dispatch: sent=%d failed=%d event=%s",
        sent,
        failed,
        cascade_event_id,
    )
    return {
        "sent": sent,
        "failed": failed,
        "notification_ids": notification_ids,
    }
