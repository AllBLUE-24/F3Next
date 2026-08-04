"""WhatsApp channel stub — implement in a later phase."""

from __future__ import annotations

from typing import Any, Optional

from shared.notification_channels.base import DeliveryResult, NotificationChannel


class WhatsAppChannel(NotificationChannel):
    channel_name = "whatsapp"

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
        return DeliveryResult(
            ok=False,
            error="WhatsApp channel not configured",
            channel=self.channel_name,
        )
