"""ERPNext implementation — full CRUD + webhook support + CVS fetchers."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Optional
from urllib.parse import quote

import httpx

from shared.erp_adapters.base import ERPAdapter
from shared.erp_adapters.circuit import AsyncCircuitBreaker

logger = logging.getLogger(__name__)


class ERPNextAdapter(ERPAdapter):
    """
    Complete ERPNext adapter implementation.
    
    All ERP I/O goes through this adapter. No direct httpx calls allowed in:
    - OS agents
    - Implementation agents
    - CVS snapshot builder
    """
    
    def __init__(self, profile: dict[str, Any]) -> None:
        super().__init__(profile)
        self._master_cb = AsyncCircuitBreaker("erpnext_master", 5, 60.0)
        self._txn_cb = AsyncCircuitBreaker("erpnext_txn", 5, 60.0)
        self._crud_cb = AsyncCircuitBreaker("erpnext_crud", 5, 60.0)

    # ── Internal Helpers ──────────────────────────────────────────────────────
    
    def _base_url(self) -> str:
        return self._profile.get("erp_url", "").rstrip("/")

    def _headers(self) -> dict[str, str]:
        api_key = self._profile.get("api_key", "")
        api_secret = self._profile.get("api_secret", "")
        return {
            "Authorization": f"token {api_key}:{api_secret}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _ssl_verify(self) -> bool:
        if self._profile.get("allow_insecure_ssl"):
            return False
        return self._profile.get("verify_ssl", True)

    def _resource_url(self, doctype: str, name: Optional[str] = None) -> str:
        """Build /api/resource/{Doctype}/{name} URL."""
        base = self._base_url()
        dt_url = quote(doctype, safe="")
        if name:
            return f"{base}/api/resource/{dt_url}/{quote(str(name), safe='')}"
        return f"{base}/api/resource/{dt_url}"

    async def _http_call(
        self,
        method: str,
        url: str,
        json_data: Optional[dict] = None,
        params: Optional[dict] = None,
        timeout: float = 30.0,
    ) -> dict[str, Any]:
        """
        Core HTTP call wrapper with error handling.
        
        Raises:
            RuntimeError — on auth errors (401/403) or server errors (5xx)
            ValueError — on bad request (4xx)
            httpx.RequestError — on network failures
        """
        async with httpx.AsyncClient(
            verify=self._ssl_verify(),
            timeout=timeout,
        ) as client:
            resp = await client.request(
                method=method.upper(),
                url=url,
                headers=self._headers(),
                json=json_data,
                params=params,
            )

            # Auth errors — raise loudly
            if resp.status_code in (401, 403):
                raise RuntimeError(
                    f"ERPNext auth error {resp.status_code} for {url}. "
                    f"Check API key permissions."
                )

            # Try to parse response body
            try:
                body = resp.json()
            except Exception:
                body = {"message": resp.text}

            # Success
            if resp.status_code in (200, 201):
                return body.get("data", body) if isinstance(body, dict) else body

            # Client errors (4xx) — non-retryable
            if 400 <= resp.status_code < 500:
                error_msg = self._parse_error(resp.status_code, body)
                raise ValueError(f"ERPNext error {resp.status_code}: {error_msg}")

            # Server errors (5xx) — retryable
            error_msg = self._parse_error(resp.status_code, body)
            raise RuntimeError(f"ERPNext server error {resp.status_code}: {error_msg}")

    def _parse_error(self, status: int, body: dict) -> str:
        """Extract human-readable error from ERPNext response."""
        if isinstance(body, str):
            return body
        exc = body.get("exception", "")
        msg = body.get("message", "")
        exc_msg = body.get("exc_message", "")
        exc_type = body.get("exc_type", "")

        if exc_type:
            return f"{exc_type}: {exc or msg or exc_msg}"
        if exc_msg:
            return exc_msg
        if exc:
            return exc.split("\n")[-1].strip() or exc
        return msg or f"HTTP {status}"

    # ── CVS Layer Fetchers ────────────────────────────────────────────────────
    
    async def fetch_master_data(self) -> dict[str, Any]:
        """
        Fetch the master_data layer snapshot from ERPNext.
        
        Returns dict with: customers, suppliers, items, warehouses, cost_centers, etc.
        """
        async def _run():
            logger.info("CVS: fetching master data for company=%s", self._profile.get("company_name"))

            # Run all fetches concurrently using adapter methods
            (
                customers,
                suppliers,
                items,
                warehouses,
                cost_centers,
                item_groups,
                territories,
                uoms,
            ) = await asyncio.gather(
                self.list_records("Customer", [
                    "name", "customer_name", "customer_group", "territory",
                    "customer_type", "disabled"
                ], filters=[["disabled", "=", 0]]),

                self.list_records("Supplier", [
                    "name", "supplier_name", "supplier_group", "supplier_type", "disabled"
                ], filters=[["disabled", "=", 0]]),

                self.list_records("Item", [
                    "name", "item_code", "item_name", "item_group",
                    "stock_uom", "weight_per_unit", "weight_uom",
                    "is_stock_item", "disabled",
                    "valuation_rate", "standard_rate"
                ], filters=[["disabled", "=", 0]]),

                self.list_records("Warehouse", [
                    "name", "warehouse_name", "warehouse_type",
                    "company", "is_group", "disabled"
                ], filters=[["disabled", "=", 0], ["is_group", "=", 0]]),

                self.list_records("Cost Center", [
                    "name", "cost_center_name", "is_group", "disabled"
                ], filters=[["disabled", "=", 0], ["is_group", "=", 0]]),

                self.list_records("Item Group", [
                    "name", "is_group"
                ], filters=[["is_group", "=", 0]]),

                self.list_records("Territory", [
                    "name", "is_group"
                ], filters=[["is_group", "=", 0]]),

                self.list_records("UOM", ["name"]),
            )

            # Build fast-lookup name sets for OS entity validation
            known_customers  = [c.get("name") or c.get("customer_name") for c in customers  if c.get("name")]
            known_suppliers  = [s.get("name") or s.get("supplier_name") for s in suppliers  if s.get("name")]
            known_items      = [i.get("item_code") or i.get("name")     for i in items      if i.get("item_code") or i.get("name")]
            known_warehouses = [w.get("name") for w in warehouses if w.get("name")]

            logger.info(
                "CVS master data: customers=%d suppliers=%d items=%d warehouses=%d",
                len(customers), len(suppliers), len(items), len(warehouses),
            )

            return {
                # Full records (for rich OS context)
                "customers":     customers,
                "suppliers":     suppliers,
                "items":         items,
                "warehouses":    warehouses,
                "cost_centers":  cost_centers,
                "item_groups":   [g["name"] for g in item_groups if g.get("name")],
                "territories":   [t["name"] for t in territories if t.get("name")],
                "uoms":          [u["name"] for u in uoms        if u.get("name")],

                # Fast-lookup name lists (injected into OS Clarity Agent prompt)
                "known_customers":  known_customers,
                "known_suppliers":  known_suppliers,
                "known_items":      known_items,
                "known_warehouses": known_warehouses,

                # Counts (for OS "status" queries)
                "counts": {
                    "customers":  len(customers),
                    "suppliers":  len(suppliers),
                    "items":      len(items),
                    "warehouses": len(warehouses),
                },
            }

        return await self._master_cb.call(_run)

    async def fetch_transaction_intel(self, days: int = 30) -> dict[str, Any]:
        """
        Fetch transaction_intel layer snapshot from ERPNext.
        
        Returns compressed transaction intelligence with recent docs, pending actions, etc.
        """
        async def _run():
            from datetime import date, timedelta
            from collections import Counter

            logger.info(
                "CVS: fetching transaction intel (last %d days) for company=%s",
                days, self._profile.get("company_name"),
            )

            since_date  = (date.today() - timedelta(days=days)).isoformat()
            company     = self._profile.get("default_company", "")

            base_filters_company = [["company", "=", company]] if company else []

            (
                open_sos,
                open_pos,
                recent_invoices,
                recent_payments,
                overdue_sinv,
            ) = await asyncio.gather(
                self.list_records("Sales Order", [
                    "name", "customer", "transaction_date", "delivery_date",
                    "grand_total", "status", "per_delivered", "per_billed"
                ], filters=base_filters_company + [
                    ["status", "in", ["To Deliver and Bill", "To Deliver", "To Bill"]],
                    ["transaction_date", ">=", since_date],
                ], limit=100),

                self.list_records("Purchase Order", [
                    "name", "supplier", "transaction_date", "schedule_date",
                    "grand_total", "status", "per_received", "per_billed"
                ], filters=base_filters_company + [
                    ["status", "in", ["To Receive and Bill", "To Receive", "To Bill"]],
                    ["transaction_date", ">=", since_date],
                ], limit=100),

                self.list_records("Sales Invoice", [
                    "name", "customer", "posting_date", "due_date",
                    "grand_total", "outstanding_amount", "status"
                ], filters=base_filters_company + [
                    ["docstatus", "=", 1],
                    ["posting_date", ">=", since_date],
                ], limit=100),

                self.list_records("Payment Entry", [
                    "name", "party_type", "party", "posting_date",
                    "paid_amount", "payment_type", "mode_of_payment"
                ], filters=base_filters_company + [
                    ["docstatus", "=", 1],
                    ["posting_date", ">=", since_date],
                ], limit=100),

                self.list_records("Sales Invoice", [
                    "name", "customer", "due_date", "outstanding_amount", "status"
                ], filters=base_filters_company + [
                    ["docstatus", "=", 1],
                    ["outstanding_amount", ">", 0],
                    ["due_date", "<", date.today().isoformat()],
                ], limit=50),
            )

            # ── Aggregation ───────────────────────────────────────────────────
            total_open_so_value  = sum(float(s.get("grand_total") or 0) for s in open_sos)
            total_open_po_value  = sum(float(p.get("grand_total") or 0) for p in open_pos)
            total_overdue_ar     = sum(float(i.get("outstanding_amount") or 0) for i in overdue_sinv)

            # Top customers by open SO count
            top_so_customers = Counter(s.get("customer") for s in open_sos if s.get("customer"))
            top_suppliers    = Counter(p.get("supplier") for p in open_pos if p.get("supplier"))

            # Pending actions (actionable items the OS surfaces proactively)
            pending_actions: list[dict] = []

            for inv in overdue_sinv:
                pending_actions.append({
                    "type":        "overdue_invoice",
                    "ref":         inv.get("name"),
                    "party":       inv.get("customer"),
                    "amount":      float(inv.get("outstanding_amount") or 0),
                    "due_date":    inv.get("due_date"),
                    "priority":    "high",
                })

            for so in open_sos:
                if float(so.get("per_delivered") or 0) < 100:
                    pending_actions.append({
                        "type":         "undelivered_so",
                        "ref":          so.get("name"),
                        "party":        so.get("customer"),
                        "amount":       float(so.get("grand_total") or 0),
                        "delivery_date": so.get("delivery_date"),
                        "priority":     "medium",
                    })

            logger.info(
                "CVS transaction intel: open_so=%d open_po=%d overdue_sinv=%d pending_actions=%d",
                len(open_sos), len(open_pos), len(overdue_sinv), len(pending_actions),
            )

            return {
                "period_days":     days,
                "as_of_date":      date.today().isoformat(),

                # Open documents
                "open_sales_orders":    open_sos,
                "open_purchase_orders": open_pos,
                "overdue_invoices":     overdue_sinv,
                "recent_invoices":      recent_invoices,
                "recent_payments":      recent_payments,

                # Actionable items
                "pending_actions": pending_actions[:20],   # Cap at 20 for context window

                # Summary (fast-read for OS prompts)
                "transaction_summary": {
                    "open_so_count":       len(open_sos),
                    "open_so_value":       round(total_open_so_value, 2),
                    "open_po_count":       len(open_pos),
                    "open_po_value":       round(total_open_po_value, 2),
                    "overdue_invoice_count": len(overdue_sinv),
                    "overdue_ar_total":    round(total_overdue_ar, 2),
                    "top_customers":       [k for k, _ in top_so_customers.most_common(5)],
                    "top_suppliers":       [k for k, _ in top_suppliers.most_common(5)],
                    "pending_action_count": len(pending_actions),
                },
            }

        return await self._txn_cb.call(_run)

    # ── CRUD Operations ───────────────────────────────────────────────────────
    
    async def create_record(
        self,
        doctype: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Create a new document via POST /api/resource/{Doctype}."""
        async def _run():
            url = self._resource_url(doctype)
            logger.debug("ERPNextAdapter.create_record: %s", doctype)
            return await self._http_call("POST", url, json_data=data)
        
        return await self._crud_cb.call(_run)

    async def update_record(
        self,
        doctype: str,
        name: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Update an existing document via PUT /api/resource/{Doctype}/{name}."""
        async def _run():
            url = self._resource_url(doctype, name)
            logger.debug("ERPNextAdapter.update_record: %s/%s", doctype, name)
            return await self._http_call("PUT", url, json_data=data)
        
        return await self._crud_cb.call(_run)

    async def get_record(
        self,
        doctype: str,
        name: str,
        fields: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """Fetch a single document via GET /api/resource/{Doctype}/{name}."""
        async def _run():
            url = self._resource_url(doctype, name)
            params = {}
            if fields:
                params["fields"] = json.dumps(fields)
            logger.debug("ERPNextAdapter.get_record: %s/%s", doctype, name)
            return await self._http_call("GET", url, params=params)
        
        return await self._crud_cb.call(_run)

    async def list_records(
        self,
        doctype: str,
        fields: list[str],
        filters: Optional[list] = None,
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        """
        Fetch a list of documents via GET /api/resource/{Doctype}.
        
        Automatically paginates if records > limit.
        """
        async def _run():
            url = self._resource_url(doctype)
            all_records: list[dict[str, Any]] = []
            page = 0
            page_size = min(limit, 1000)
            max_pages = 100

            while page < max_pages:
                params: dict[str, Any] = {
                    "fields": json.dumps(fields),
                    "limit_page_length": page_size,
                    "limit_start": page * page_size,
                }
                if filters:
                    params["filters"] = json.dumps(filters)

                logger.debug(
                    "ERPNextAdapter.list_records: %s page=%d limit_start=%d",
                    doctype, page, page * page_size,
                )

                body = await self._http_call("GET", url, params=params)
                
                # Handle both {"data": [...]} and direct list responses
                if isinstance(body, dict) and "data" in body:
                    page_records = body["data"]
                elif isinstance(body, list):
                    page_records = body
                else:
                    page_records = []

                all_records.extend(page_records)

                # ERPNext signals "last page" by returning fewer records than requested
                if len(page_records) < page_size:
                    break

                page += 1

            logger.debug(
                "ERPNextAdapter.list_records: %s total=%d pages=%d",
                doctype, len(all_records), page + 1,
            )
            return all_records
        
        return await self._crud_cb.call(_run)

    async def submit_document(self, doctype: str, name: str) -> dict[str, Any]:
        """Submit a document by setting docstatus=1."""
        return await self.update_record(doctype, name, {"docstatus": 1})

    async def cancel_document(self, doctype: str, name: str) -> dict[str, Any]:
        """Cancel a document by setting docstatus=2."""
        return await self.update_record(doctype, name, {"docstatus": 2})

    async def delete_record(self, doctype: str, name: str) -> bool:
        """Delete a document via DELETE /api/resource/{Doctype}/{name}."""
        async def _run():
            url = self._resource_url(doctype, name)
            logger.debug("ERPNextAdapter.delete_record: %s/%s", doctype, name)
            await self._http_call("DELETE", url)
            return True
        
        try:
            return await self._crud_cb.call(_run)
        except Exception as e:
            logger.warning("ERPNextAdapter.delete_record failed: %s", e)
            return False

    # ── Webhook Management ────────────────────────────────────────────────────
    
    async def register_webhook(
        self,
        doctype: str,
        event: str,
        callback_url: str,
        webhook_secret: str,
        field_list: list[str],
    ) -> bool:
        """
        Create a Frappe Webhook document for the specified doctype+event.
        
        Returns True if webhook was created or already exists.
        """
        try:
            # Check if webhook already exists
            existing = await self.list_records(
                "Webhook",
                ["name"],
                filters=[
                    ["webhook_doctype", "=", doctype],
                    ["request_url", "=", callback_url],
                    ["webhook_docevent", "=", event],
                ],
                limit=1,
            )

            if existing:
                logger.info(
                    "ERPNextAdapter.register_webhook: already exists — %s %s",
                    doctype, event,
                )
                return True

            # Build webhook data fields
            webhook_data = [{"fieldname": f, "key": f} for f in field_list]
            if not any(d["key"] == "name" for d in webhook_data):
                webhook_data.insert(0, {"fieldname": "name", "key": "name"})

            # Create webhook
            payload = {
                "webhook_doctype": doctype,
                "webhook_docevent": event,
                "request_url": callback_url,
                "request_method": "POST",
                "request_structure": "Form URL-Encoded",
                "enable_security": 1,
                "webhook_secret": webhook_secret,
                "webhook_data": webhook_data,
                "webhook_json": f'{{"doctype": "{doctype}"}}',
            }

            await self.create_record("Webhook", payload)
            logger.info(
                "ERPNextAdapter.register_webhook: registered — %s %s",
                doctype, event,
            )
            return True

        except Exception as e:
            logger.error(
                "ERPNextAdapter.register_webhook: FAILED — %s %s: %s",
                doctype, event, e,
            )
            return False

    async def unregister_webhook(
        self,
        doctype: str,
        event: str,
        callback_url: str,
    ) -> bool:
        """
        Remove a Frappe Webhook document.
        
        Returns True if webhook was deleted or didn't exist.
        """
        try:
            # Find matching webhook
            existing = await self.list_records(
                "Webhook",
                ["name"],
                filters=[
                    ["webhook_doctype", "=", doctype],
                    ["request_url", "=", callback_url],
                    ["webhook_docevent", "=", event],
                ],
                limit=1,
            )

            if not existing:
                logger.info(
                    "ERPNextAdapter.unregister_webhook: not found — %s %s",
                    doctype, event,
                )
                return True

            # Delete webhook
            webhook_name = existing[0]["name"]
            await self.delete_record("Webhook", webhook_name)
            logger.info(
                "ERPNextAdapter.unregister_webhook: deleted — %s %s",
                doctype, event,
            )
            return True

        except Exception as e:
            logger.error(
                "ERPNextAdapter.unregister_webhook: FAILED — %s %s: %s",
                doctype, event, e,
            )
            return False
