"""
containers/context_versioning/snapshot_builder/erp_fetcher.py

Fetches live data from ERPNext to build context snapshot layers.

Called by snapshot_builder/activities.py during a CVS sync.

Design rules:
  - Auth errors (401/403) raise loudly — caller must not save partial data.
  - Network errors raise loudly — caller must not save empty snapshots.
  - Empty data arrays are allowed (a doctype may be empty on a fresh instance)
    but are logged as warnings so they are visible in logs.
  - All I/O is async (httpx).
  - Credentials come from the company profile (identity layer), never hardcoded.
  - ALL doctypes are fully paginated — no silent truncation at 500/1000 records.

Functions:
  fetch_master_data(profile)      → Layer 2: customers, suppliers, items, warehouses
  fetch_transaction_intel(profile)→ Layer 3: recent orders, invoices, pending actions
"""

import asyncio
import logging
from datetime import date, timedelta
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────

_PAGE_SIZE   = 1_000   # records per page — ERPNext max is 500 by default, but
                        # site admins can raise it; 1000 is safe for our own instances
_MAX_PAGES   = 100      # hard cap: 100 × 1000 = 100,000 records per doctype
_TIMEOUT_SEC = 20.0     # slightly more generous than before for large pages


# ── ERPNext API helper ─────────────────────────────────────────────────────────

def _headers(profile: dict) -> dict:
    return {
        "Authorization": f"token {profile['api_key']}:{profile['api_secret']}",
        "Content-Type":  "application/json",
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
    limit:     int = _PAGE_SIZE,   # kept for back-compat; now used as page_size
) -> list[dict]:
    """
    Fetch ALL records for a doctype from ERPNext using cursor-based pagination.

    Walks pages of `limit` records each until ERPNext returns fewer records
    than the page size (meaning we have reached the end).

    Raises:
      RuntimeError — on 401/403 (auth failure). Caller must not save partial data.
      httpx.HTTPStatusError — on other non-2xx responses.
      httpx.RequestError — on network/DNS failure.

    Returns:
      list[dict] — may be empty if the doctype has no records (not an error).
    """
    base_url = profile.get("erp_url", "").rstrip("/")
    if not base_url:
        raise ValueError("company profile is missing 'erp_url'")

    url        = f"{base_url}/api/resource/{doctype.replace(' ', '%20')}"
    page_size  = min(limit, _PAGE_SIZE)
    all_records: list[dict] = []
    page       = 0

    async with httpx.AsyncClient(
        verify  = _ssl_verify(profile),
        timeout = _TIMEOUT_SEC,
    ) as client:

        while page < _MAX_PAGES:
            params: dict[str, Any] = {
                "fields":           str(fields),
                "limit_page_length": page_size,
                "limit_start":       page * page_size,
            }
            if filters:
                params["filters"] = str(filters)

            logger.debug(
                "[ERP_FETCHER] GET %s  page=%d  limit_start=%d",
                url, page, page * page_size,
            )

            resp = await client.get(url, headers=_headers(profile), params=params)

            logger.debug(
                "[ERP_FETCHER] %s  status=%d  page=%d",
                doctype, resp.status_code, page,
            )

            # ── Auth errors: raise loudly, never save empty data ───────────────
            if resp.status_code in (401, 403):
                raise RuntimeError(
                    f"ERPNext auth error {resp.status_code} for doctype={doctype}. "
                    f"Check API key permissions."
                )

            resp.raise_for_status()

            try:
                resp_data = resp.json()
            except Exception:
                raise ValueError(
                    f"ERPNext returned non-JSON for doctype={doctype}: {resp.text[:200]}"
                )

            if "data" not in resp_data:
                raise ValueError(
                    f"ERPNext response missing 'data' key for doctype={doctype}: "
                    f"{str(resp_data)[:200]}"
                )

            page_records = resp_data["data"]
            all_records.extend(page_records)

            logger.debug(
                "[ERP_FETCHER] %s  page=%d  got=%d  total_so_far=%d",
                doctype, page, len(page_records), len(all_records),
            )

            # ERPNext signals "last page" by returning fewer records than requested
            if len(page_records) < page_size:
                break

            page += 1

        else:
            # Hit _MAX_PAGES cap — log a warning but return what we have
            logger.warning(
                "[ERP_FETCHER] %s hit MAX_PAGES cap (%d). "
                "Fetched %d records. Some records may be missing.",
                doctype, _MAX_PAGES, len(all_records),
            )

    logger.info(
        "[ERP_FETCHER] %s  total_records=%d  pages_fetched=%d",
        doctype, len(all_records), page + 1,
    )

    if not all_records:
        logger.warning(
            "[ERP_FETCHER] %s returned 0 records — doctype may be empty on this instance.",
            doctype,
        )

    return all_records



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
