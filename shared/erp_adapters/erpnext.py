"""ERPNext implementation — delegates to existing fetchers with circuit breaker."""

from __future__ import annotations

import logging
from typing import Any

from shared.erp_adapters.base import ERPAdapter
from shared.erp_adapters.circuit import AsyncCircuitBreaker

logger = logging.getLogger(__name__)


class ERPNextAdapter(ERPAdapter):
    def __init__(self, profile: dict[str, Any]) -> None:
        super().__init__(profile)
        self._master_cb = AsyncCircuitBreaker("erpnext_master", 5, 60.0)
        self._txn_cb = AsyncCircuitBreaker("erpnext_txn", 5, 60.0)

    async def fetch_master_data(self) -> dict[str, Any]:
        async def _run():
            from containers.context_versioning.snapshot_builder import erp_fetcher

            return await erp_fetcher.fetch_master_data(self._profile)

        return await self._master_cb.call(_run)

    async def fetch_transaction_intel(self, days: int = 30) -> dict[str, Any]:
        async def _run():
            from containers.context_versioning.snapshot_builder import erp_fetcher

            return await erp_fetcher.fetch_transaction_intel(self._profile, days=days)

        return await self._txn_cb.call(_run)

    async def register_webhook(
        self,
        doctype: str,
        event: str,
        callback_url: str,
        webhook_secret: str,
        field_list: list[str],
    ) -> bool:
        logger.debug("ERPNextAdapter.register_webhook stub: %s %s", doctype, event)
        return False
