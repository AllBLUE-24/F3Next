"""Abstract notification channel interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class DeliveryResult:
    ok: bool
    notification_id: Optional[str] = None
    error: Optional[str] = None
    channel: str = "in_app"


class NotificationChannel(ABC):
    channel_name: str = "base"

    @abstractmethod
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
        """Deliver one notification to a recipient."""
