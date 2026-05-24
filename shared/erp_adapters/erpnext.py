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

            # ── Optional extension: additional master doctypes via Tier1 doctype_graph ──
            entities_by_doctype: dict[str, Any] = {}
            known_names: dict[str, list[str]] = {}
            counts: dict[str, int] = {}

            def _add_bucket(key: str, records: Any, *, known: Optional[list[str]] = None) -> None:
                entities_by_doctype[key] = records
                if known is None:
                    if isinstance(records, list):
                        known = [str(r.get("name")) for r in records if isinstance(r, dict) and r.get("name")]
                    else:
                        known = []
                known_names[key] = known
                counts[key] = len(records) if isinstance(records, list) else 0

            _add_bucket("customers", customers, known=known_customers)
            _add_bucket("suppliers", suppliers, known=known_suppliers)
            _add_bucket("items", items, known=known_items)
            _add_bucket("warehouses", warehouses, known=known_warehouses)
            _add_bucket("cost_centers", cost_centers)
            _add_bucket("item_groups", [g["name"] for g in item_groups if g.get("name")])
            _add_bucket("territories", [t["name"] for t in territories if t.get("name")])
            _add_bucket("uoms", [u["name"] for u in uoms if u.get("name")])

            try:
                from shared.context_engine.loader import Tier1Loader

                tier1, _ = Tier1Loader().load()
                doctypes = ((tier1.get("doctype_graph") or {}).get("doctypes") or {})
                extras: list[tuple[str, dict]] = []
                for dt_name, dt_spec in doctypes.items():
                    cfg = (dt_spec or {}).get("cvs_config") or {}
                    if not cfg or not cfg.get("include_in_snapshot"):
                        continue
                    # Skip ones we already fetched above
                    if dt_name in {"Customer", "Supplier", "Item", "Warehouse", "Cost Center", "Item Group", "Territory", "UOM"}:
                        continue
                    extras.append((dt_name, cfg))

                if extras:
                    tasks = []
                    meta: list[tuple[str, str]] = []  # (doctype, registry_key)
                    for dt_name, cfg in extras:
                        registry_key = str(cfg.get("registry_key") or "").strip() or dt_name.lower().replace(" ", "_") + "s"
                        fields = cfg.get("fetch_fields") or ["name"]
                        filters = cfg.get("filters")
                        limit = int(cfg.get("limit") or 1000)
                        tasks.append(self.list_records(dt_name, fields, filters=filters, limit=limit))
                        meta.append((dt_name, registry_key))

                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    for (dt_name, registry_key), res in zip(meta, results):
                        if isinstance(res, Exception):
                            logger.warning("CVS master extra fetch failed for %s: %s", dt_name, res)
                            continue
                        if isinstance(res, list):
                            _add_bucket(registry_key, res)
            except Exception as e:
                logger.debug("CVS master dynamic extension skipped: %s", e)

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

                # Generic, doctype-agnostic registry (new; backward compatible)
                "entities_by_doctype": entities_by_doctype,
                "known_names": known_names,
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
            # 1. Resolve link references dynamically (e.g. Main -> Main - GS)
            resolved_data = await self._resolve_link_references(doctype, data)

            # 2. Check if the record already exists first to avoid duplicate inserts
            name_val = resolved_data.get("name")
            if not name_val:
                _DT_NAME_FIELD = {
                    "UOM":                      "uom_name",
                    "Item Group":               "item_group_name",
                    "Customer Group":           "customer_group_name",
                    "Supplier Group":           "supplier_group_name",
                    "Territory":                "territory_name",
                    "Price List":               "price_list_name",
                    "Currency":                 "currency_name",
                    "Country":                  "country_name",
                    "Department":               "department_name",
                    "Designation":              "designation_name",
                    "Sales Stage":              "stage_name",
                    "Lead Source":              "source_name",
                    "Incoterm":                 "incoterm",
                    "Industry Type":            "industry",
                    "Item Attribute":           "attribute_name",
                    "Fiscal Year":              "year",
                    "Sales Person":             "sales_person_name",
                    "Payment Terms Template":   "template_name",
                    "Mode of Payment":          "mode_of_payment",
                    "Warehouse Type":           "warehouse_type_name",
                }
                name_field = _DT_NAME_FIELD.get(doctype)
                if not name_field:
                    try:
                        schema = await self.get_doctype_schema(doctype)
                        for f in schema:
                            if f.get("reqd") == 1 and f.get("fieldtype") in ("Data", "Link"):
                                name_field = f["fieldname"]
                                break
                    except Exception:
                        pass
                if name_field:
                    name_val = resolved_data.get(name_field)

            if name_val:
                try:
                    exists = await self.list_records(doctype, ["name"], filters=[["name", "=", name_val]], limit=1)
                    if exists:
                        logger.info("Record %s '%s' already exists — skipping creation", doctype, name_val)
                        return exists[0]
                except Exception:
                    pass

            url = self._resource_url(doctype)
            logger.debug("ERPNextAdapter.create_record: %s", doctype)
            return await self._http_call("POST", url, json_data=resolved_data)
        
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

    # ── Schema Introspection ──────────────────────────────────────────────────

    async def get_doctype_schema(self, doctype: str) -> list[dict]:
        """
        Fetch the field definitions for a doctype directly from the live ERPNext instance.

        Uses: GET /api/resource/DocType/{doctype}
              → data.fields[] contains all field definitions

        Skips structural fields (Column Break, Section Break, Tab Break, HTML)
        since they carry no data and would pollute the mapping schema.

        Returns list of dicts:
            [{"fieldname": str, "fieldtype": str, "reqd": 0|1, "label": str}, ...]

        Raises ValueError if the doctype doesn't exist (404).
        Raises RuntimeError on network/auth failure.
        """
        _SKIP_TYPES = {
            "Column Break", "Section Break", "Tab Break",
            "HTML", "Heading", "Button", "Fold",
        }

        url = self._resource_url("DocType", doctype)
        logger.info("ERPNextAdapter.get_doctype_schema: fetching live schema for %s", doctype)

        raw = await self._http_call("GET", url)

        # Frappe returns: {"data": {"fields": [...], ...}} or unwrapped by _http_call → {"fields": [...]}
        fields_raw = (
            raw.get("fields")
            or (raw.get("data") or {}).get("fields")
            or []
        )

        fields: list[dict] = []
        for f in fields_raw:
            if not isinstance(f, dict):
                continue
            ft = str(f.get("fieldtype") or "").strip()
            if ft in _SKIP_TYPES:
                continue
            fname = str(f.get("fieldname") or "").strip()
            if not fname:
                continue
            fields.append({
                "fieldname": fname,
                "fieldtype": ft,
                "reqd":      int(f.get("reqd") or 0),
                "label":     str(f.get("label") or fname),
                "options":   f.get("options"),   # Link target doctype
                "default":   f.get("default"),
            })

        logger.info(
            "ERPNextAdapter.get_doctype_schema: %s → %d fields",
            doctype, len(fields),
        )
        return fields

    async def _resolve_link_references(self, doctype: str, data: dict[str, Any]) -> dict[str, Any]:
        """
        Inspects the DocType schema for any Link fields. If a referenced value
        does not exist exactly, it dynamically queries the target doctype to see
        if a company-abbreviated suffix (like 'Main - GS') exists, or if a base
        value match (like 'WIP - Factory' -> 'WIP - GS') exists, and updates the reference.
        """
        if doctype == "DocType":
            return data

        try:
            schema_fields = await self.get_doctype_schema(doctype)
            link_fields = {f["fieldname"]: f["options"] for f in schema_fields if f.get("fieldtype") == "Link" and f.get("options")}
            
            for fieldname, target_dt in link_fields.items():
                val = data.get(fieldname)
                if not val or not isinstance(val, str):
                    continue
                
                # 1. Check if it already exists exactly as is
                exists = await self.list_records(target_dt, ["name"], filters=[["name", "=", val]], limit=1)
                if exists:
                    continue
                
                # 2. Check if a suffix match exists (e.g. 'Main' -> 'Main - GS')
                suffix_match = await self.list_records(
                    target_dt,
                    ["name"],
                    filters=[["name", "like", f"{val} - %"]],
                    limit=1
                )
                if suffix_match and suffix_match[0].get("name"):
                    matched_name = suffix_match[0]["name"]
                    logger.info("Dynamically resolved link reference for %s.%s: '%s' -> '%s'", doctype, fieldname, val, matched_name)
                    data[fieldname] = matched_name
                    continue

                # 3. Check if base name splits match (e.g. 'WIP - Factory' -> 'WIP - GS')
                if " - " in val:
                    base_val = val.split(" - ")[0].strip()
                    base_match = await self.list_records(
                        target_dt,
                        ["name"],
                        filters=[["name", "like", f"{base_val} - %"]],
                        limit=1
                    )
                    if base_match and base_match[0].get("name"):
                        matched_name = base_match[0]["name"]
                        logger.info("Dynamically resolved base link reference for %s.%s: '%s' -> '%s'", doctype, fieldname, val, matched_name)
                        data[fieldname] = matched_name
                        continue
        except Exception as e:
            logger.debug("Failed to resolve link references for %s: %s", doctype, e)
            
        return data

    async def seed_from_config(self, doctype: str, project_details: dict[str, Any]) -> None:
        """ERPNext-specific logic to seed/initialize configuration doctypes like Fiscal Year and Warehouses."""
        if doctype == "Fiscal Year":
            country = project_details.get("country") or "India"
            fiscal_year_val = "2026-2027"
            if country == "India":
                start_date = "2026-04-01"
                end_date = "2027-03-31"
            else:
                start_date = "2026-01-01"
                end_date = "2026-12-31"
                fiscal_year_val = "2026"

            record = {
                "year": fiscal_year_val,
                "year_start_date": start_date,
                "year_end_date": end_date,
            }

            # Check if already exists first
            exists = await self.list_records("Fiscal Year", ["name"], filters=[["name", "=", fiscal_year_val]], limit=1)
            if not exists:
                try:
                    await self.create_record("Fiscal Year", record)
                    logger.info("Seeded Fiscal Year %s (%s to %s) successfully from config", fiscal_year_val, start_date, end_date)
                except Exception as e:
                    logger.error("Failed to seed Fiscal Year %s: %s", fiscal_year_val, e)
            else:
                logger.info("Fiscal Year %s already exists — skipping", fiscal_year_val)

        elif doctype == "Warehouse":
            existing_whs = await self.list_records("Warehouse", ["name", "company", "is_group"])
            if not existing_whs:
                logger.warning("No warehouses found to seed children from")
                return

            company = existing_whs[0].get("company")
            parent_wh = None
            abbr = ""
            for wh in existing_whs:
                if wh.get("is_group") == 1 or "all warehouses" in wh.get("name", "").lower():
                    parent_wh = wh["name"]
                    if " - " in parent_wh:
                        abbr = parent_wh.split(" - ")[-1].strip()
                    break
            
            if not parent_wh:
                parent_wh = existing_whs[0]["name"]
                if " - " in parent_wh:
                    abbr = parent_wh.split(" - ")[-1].strip()

            if not abbr and company:
                abbr = "".join([w[0] for w in company.split() if w]).upper()

            # Seed standard manufacturing child warehouses (Stores and WIP) under the parent group
            for wh_base in ("Stores", "WIP"):
                wh_name = f"{wh_base} - {abbr}" if abbr else wh_base
                exists = await self.list_records("Warehouse", ["name"], filters=[["name", "=", wh_name]], limit=1)
                if not exists:
                    wh_record = {
                        "warehouse_name": wh_base,
                        "company": company,
                        "parent_warehouse": parent_wh,
                        "is_group": 0
                    }
                    try:
                        await self.create_record("Warehouse", wh_record)
                        logger.info("Auto-seeded manufacturing child warehouse '%s' successfully under parent '%s'", wh_name, parent_wh)
                    except Exception as e:
                        logger.error("Failed to seed child warehouse %s: %s", wh_name, e)
