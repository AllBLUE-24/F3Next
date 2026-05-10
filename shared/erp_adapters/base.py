"""Abstract ERP adapter — multi-ERP ready surface for CVS and tools."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional


class ERPAdapter(ABC):
    """
    Multi-ERP adapter interface.
    
    Provides a unified API for all ERP operations used by:
    - CVS snapshot builder (fetch_master_data, fetch_transaction_intel)
    - OS execution agent (create_record, update_record, submit_document, etc.)
    - Implementation import agent (bulk creates, list operations)
    - Webhook registration (register_webhook)
    """

    def __init__(self, profile: dict[str, Any]) -> None:
        self._profile = profile

    # ── CVS Layer Fetchers ────────────────────────────────────────────────────
    
    @abstractmethod
    async def fetch_master_data(self) -> dict[str, Any]:
        """Fetch master_data layer snapshot payload."""

    @abstractmethod
    async def fetch_transaction_intel(self, days: int = 30) -> dict[str, Any]:
        """Fetch transaction_intel layer snapshot payload."""

    # ── CRUD Operations ───────────────────────────────────────────────────────
    
    @abstractmethod
    async def create_record(
        self,
        doctype: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Create a new document in the ERP.
        
        Returns:
            Created document dict with at least {"name": str, ...}
        """

    @abstractmethod
    async def update_record(
        self,
        doctype: str,
        name: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Update an existing document in the ERP.
        
        Returns:
            Updated document dict with at least {"name": str, ...}
        """

    @abstractmethod
    async def get_record(
        self,
        doctype: str,
        name: str,
        fields: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """
        Fetch a single document by name.
        
        Returns:
            Document dict with requested fields, or full doc if fields is None
        """

    @abstractmethod
    async def list_records(
        self,
        doctype: str,
        fields: list[str],
        filters: Optional[list] = None,
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        """
        Fetch a list of documents matching filters.
        
        Returns:
            List of document dicts with requested fields.
            Empty list if no records found (not an error).
        """

    @abstractmethod
    async def submit_document(self, doctype: str, name: str) -> dict[str, Any]:
        """
        Submit a document (set docstatus=1).
        
        Returns:
            Submitted document dict
        """

    @abstractmethod
    async def cancel_document(self, doctype: str, name: str) -> dict[str, Any]:
        """
        Cancel a document (set docstatus=2).
        
        Returns:
            Cancelled document dict
        """

    @abstractmethod
    async def delete_record(self, doctype: str, name: str) -> bool:
        """
        Delete a document from the ERP.
        
        Returns:
            True if deleted successfully
        """

    # ── Webhook Management ────────────────────────────────────────────────────
    
    @abstractmethod
    async def register_webhook(
        self,
        doctype: str,
        event: str,
        callback_url: str,
        webhook_secret: str,
        field_list: list[str],
    ) -> bool:
        """
        Create a single webhook configuration in the ERP.
        
        Returns:
            True if webhook was created or already exists
        """

    @abstractmethod
    async def unregister_webhook(
        self,
        doctype: str,
        event: str,
        callback_url: str,
    ) -> bool:
        """
        Remove a webhook configuration from the ERP.
        
        Returns:
            True if webhook was deleted or didn't exist
        """

    # ── Utility Methods ───────────────────────────────────────────────────────
    
    def normalize_field_name(self, doctype: str, field: str) -> str:
        """Hook for ERP-specific naming; default passthrough."""
        return field

    async def get_doctype_schema(
        self,
        doctype: str,
    ) -> list[dict]:
        """
        Fetch the raw field definitions for a doctype from the live ERP instance.

        Returns a list of field dicts, each with at least:
            { "fieldname": str, "fieldtype": str, "reqd": 0|1, "label": str }

        Default implementation raises NotImplementedError so subclasses must
        implement this if they support the schema API.
        """
        raise NotImplementedError(f"{self.__class__.__name__} does not implement get_doctype_schema")
