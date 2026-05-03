"""Abstract ERP adapter — multi-ERP ready surface for CVS and tools."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional


class ERPAdapter(ABC):
    """Minimal read/write surface used by CVS snapshot builder today."""

    def __init__(self, profile: dict[str, Any]) -> None:
        self._profile = profile

    @abstractmethod
    async def fetch_master_data(self) -> dict[str, Any]:
        """Layer: master_data snapshot payload."""

    @abstractmethod
    async def fetch_transaction_intel(self, days: int = 30) -> dict[str, Any]:
        """Layer: transaction_intel snapshot payload."""

    @abstractmethod
    async def register_webhook(
        self,
        doctype: str,
        event: str,
        callback_url: str,
        webhook_secret: str,
        field_list: list[str],
    ) -> bool:
        """Create a single webhook on the ERP (ERPNext Webhook doc)."""

    def normalize_field_name(self, doctype: str, field: str) -> str:
        """Hook for ERP-specific naming; default passthrough."""
        return field
