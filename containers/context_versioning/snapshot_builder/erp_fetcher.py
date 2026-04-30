"""
containers/context_versioning/snapshot_builder/erp_fetcher.py

Fetches live data from ERPNext to build context snapshot layers.

Called by snapshot_builder/activities.py during a CVS sync.

Design rules:
  - Never raises — all errors are caught and logged; partial data is returned
  - Uses the ERPNext REST API (same pattern as execution_agent)
  - All I/O is async (httpx)
  - Credentials come from the company profile (identity layer), never hardcoded

Functions:
  fetch_master_data(profile)      → Layer 2: customers, suppliers, items, warehouses
  fetch_transaction_intel(profile)→ Layer 3: recent orders, invoices, pending actions
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

# ── ERPNext API helper ─────────────────────────────────────────────────────────

def _headers(profile: dict) -> dict:
    return {
        "Authorization": f"token {profile['api_key']}:{profile['api_secret']}",
        "Content-Type": "application/json",
    }


def _ssl_verify(profile: dict) -> bool:
    if profile.get("allow_insecure_ssl"):
        return False
    return profile.get("verify_ssl", True)


async def _get_list(
    profile:   dict,
    doctype:   str,
    fields:    list[str],
    filters:   Optional[list] = None,
    limit:     int = 500,
) -> list[dict]:
    """
    Call the ERPNext /api/resource/{doctype} list endpoint.
    Returns [] on any failure (network, auth, doctype not found).
    """
    base_url = profile.get("erp_url", "").rstrip("/")
    if not base_url:
        return []

    params: dict[str, Any] = {
        "fields":    str(fields),
        "limit_page_length": limit,
    }
    if filters:
        params["filters"] = str(filters)

    url = f"{base_url}/api/resource/{doctype.replace(' ', '%20')}"

    try:
        async with httpx.AsyncClient(
            verify=_ssl_verify(profile),
            timeout=15.0,
        ) as client:
            resp = await client.get(url, headers=_headers(profile), params=params)
            resp.raise_for_status()
            return resp.json().get("data", [])
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 403:
            logger.warning("ERPNext 403 for %s — check API permissions", doctype)
        else:
            logger.warning("ERPNext %s returned %d for doctype %s", base_url, e.response.status_code, doctype)
        return []
    except Exception as e:
        logger.error("ERPNext fetch failed for doctype=%s: %s", doctype, e)
        return []


# ── Layer 2: Master Data ───────────────────────────────────────────────────────

async def fetch_master_data(profile: dict) -> dict:
    """
    Fetch the master data registry from ERPNext.

    Returns a dict with:
      customers, suppliers, items, warehouses, cost_centers
      Each is a list of dicts with the key fields needed by OS.

    Never raises — returns partial data if some doctypes fail.
    """
    logger.info("CVS: fetching master data for company=%s", profile.get("company_name"))

    # Run all fetches concurrently
    import asyncio

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
        _get_list(profile, "Customer", [
            "name", "customer_name", "customer_group", "territory",
            "customer_type", "disabled"
        ], filters=[["disabled", "=", 0]]),

        _get_list(profile, "Supplier", [
            "name", "supplier_name", "supplier_group", "supplier_type", "disabled"
        ], filters=[["disabled", "=", 0]]),

        _get_list(profile, "Item", [
            "name", "item_code", "item_name", "item_group",
            "stock_uom", "weight_per_unit", "weight_uom",
            "is_stock_item", "disabled",
            "valuation_rate", "standard_rate"
        ], filters=[["disabled", "=", 0]]),

        _get_list(profile, "Warehouse", [
            "name", "warehouse_name", "warehouse_type",
            "company", "is_group", "disabled"
        ], filters=[["disabled", "=", 0], ["is_group", "=", 0]]),

        _get_list(profile, "Cost Center", [
            "name", "cost_center_name", "is_group", "disabled"
        ], filters=[["disabled", "=", 0], ["is_group", "=", 0]]),

        _get_list(profile, "Item Group", [
            "name", "is_group"
        ], filters=[["is_group", "=", 0]]),

        _get_list(profile, "Territory", [
            "name", "is_group"
        ], filters=[["is_group", "=", 0]]),

        _get_list(profile, "UOM", ["name"]),
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


# ── Layer 3: Transaction Intelligence ─────────────────────────────────────────

async def fetch_transaction_intel(profile: dict, days: int = 30) -> dict:
    """
    Fetch recent transaction data from ERPNext.

    Returns a compressed transaction intelligence dict with:
      - recent_documents: last N submitted documents across key doctypes
      - open_orders: open Sales Orders and Purchase Orders
      - overdue_invoices: invoices past due date
      - transaction_summary: aggregated counts and amounts
      - pending_actions: actionable items the OS can surface proactively

    Never raises — returns partial data if some queries fail.
    """
    logger.info(
        "CVS: fetching transaction intel (last %d days) for company=%s",
        days, profile.get("company_name"),
    )

    import asyncio

    since_date  = (date.today() - timedelta(days=days)).isoformat()
    company     = profile.get("default_company", "")

    base_filters_company = [["company", "=", company]] if company else []

    (
        open_sos,
        open_pos,
        recent_invoices,
        recent_payments,
        overdue_sinv,
    ) = await asyncio.gather(
        _get_list(profile, "Sales Order", [
            "name", "customer", "transaction_date", "delivery_date",
            "grand_total", "status", "per_delivered", "per_billed"
        ], filters=base_filters_company + [
            ["status", "in", ["To Deliver and Bill", "To Deliver", "To Bill"]],
            ["transaction_date", ">=", since_date],
        ], limit=100),

        _get_list(profile, "Purchase Order", [
            "name", "supplier", "transaction_date", "schedule_date",
            "grand_total", "status", "per_received", "per_billed"
        ], filters=base_filters_company + [
            ["status", "in", ["To Receive and Bill", "To Receive", "To Bill"]],
            ["transaction_date", ">=", since_date],
        ], limit=100),

        _get_list(profile, "Sales Invoice", [
            "name", "customer", "posting_date", "due_date",
            "grand_total", "outstanding_amount", "status"
        ], filters=base_filters_company + [
            ["docstatus", "=", 1],
            ["posting_date", ">=", since_date],
        ], limit=100),

        _get_list(profile, "Payment Entry", [
            "name", "party_type", "party", "posting_date",
            "paid_amount", "payment_type", "mode_of_payment"
        ], filters=base_filters_company + [
            ["docstatus", "=", 1],
            ["posting_date", ">=", since_date],
        ], limit=100),

        _get_list(profile, "Sales Invoice", [
            "name", "customer", "due_date", "outstanding_amount", "status"
        ], filters=base_filters_company + [
            ["docstatus", "=", 1],
            ["outstanding_amount", ">", 0],
            ["due_date", "<", date.today().isoformat()],
        ], limit=50),
    )

    # ── Aggregation ───────────────────────────────────────────────────────────
    total_open_so_value  = sum(float(s.get("grand_total") or 0) for s in open_sos)
    total_open_po_value  = sum(float(p.get("grand_total") or 0) for p in open_pos)
    total_overdue_ar     = sum(float(i.get("outstanding_amount") or 0) for i in overdue_sinv)

    # Top customers by open SO count
    from collections import Counter
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
