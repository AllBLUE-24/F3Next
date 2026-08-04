"""In-app notification channel — writes to notifications table."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from shared.database.db import AsyncSessionLocal
from shared.models.notification_models import Notification
from shared.notification_channels.base import DeliveryResult, NotificationChannel


class InAppChannel(NotificationChannel):
    channel_name = "in_app"

    async def send(
        self,
        *,
        project_id: str,
        recipient_client_id: str,
        department: Optional[str],
        title: str,
        body: str,
        payload: dict[str, Any],
        risk_tier: str,
        cascade_event_id: Optional[str] = None,
    ) -> DeliveryResult:
        notif_id = uuid.uuid4()
        now = datetime.now(timezone.utc)

        async with AsyncSessionLocal() as session:
            row = Notification(
                id=notif_id,
                cascade_event_id=uuid.UUID(cascade_event_id) if cascade_event_id else None,
                project_id=uuid.UUID(str(project_id)),
                recipient_client_id=recipient_client_id,
                department=department,
                channel=self.channel_name,
                title=title[:500],
                body=body,
                payload=payload or {},
                risk_tier=risk_tier,
                status="sent",
                delivered_at=now,
            )
            session.add(row)
            await session.commit()

        return DeliveryResult(
            ok=True,
            notification_id=str(notif_id),
            channel=self.channel_name,
        )
