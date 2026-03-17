"""Execution Agent: POST payload to ERPNext API (or simulate in demo mode)."""
from typing import Any

import httpx

from config import DEMO_MODE, ERPNEXT_URL, get_erpnext_auth


def _simulate_sales_order(payload: dict, clarity_entities: dict | None = None) -> dict[str, Any]:
    """Simulate successful SO creation when ERPNext is not available."""
    # Prefer clarity entities for total (LLM output); fall back to payload
    entity_items = (clarity_entities or {}).get("items", [])
    payload_items = payload.get("items", [])
    total = 0
    for i, it in enumerate(entity_items or payload_items):
        qty = it.get("qty") or 0
        rate = it.get("rate") or it.get("price")  # LLM may use "price" or "rate"
        if rate is None and i < len(payload_items):
            rate = payload_items[i].get("rate") or payload_items[i].get("price")
        if rate is not None and rate != "":
            try:
                total += float(qty) * float(rate)
            except (TypeError, ValueError):
                pass
    return {
        "success": True,
        "result": {
            "name": "SO-DEMO-001",
            "customer": payload.get("customer", ""),
            "grand_total": total,
            "docstatus": 0,
            "doctype": "Sales Order",
        },
        "error": None,
    }


def execute_sales_order(payload: dict, clarity_entities: dict | None = None) -> dict[str, Any]:
    """
    Create Sales Order in ERPNext via API.
    In DEMO_MODE: simulate success (no ERPNext needed).
    Returns: { success: bool, result: {...}, error: str }
    """
    if DEMO_MODE:
        return _simulate_sales_order(payload, clarity_entities)

    if not ERPNEXT_URL:
        return {"success": False, "error": "ERPNEXT_URL not configured", "result": None}

    api_key, api_secret = get_erpnext_auth()
    if not api_key or not api_secret:
        return {"success": False, "error": "ERPNext API credentials not configured", "result": None}

    url = f"{ERPNEXT_URL}/api/resource/Sales Order"
    auth = (api_key, api_secret)
    headers = {"Content-Type": "application/json"}

    try:
        r = httpx.post(url, auth=auth, json=payload, headers=headers, timeout=30)
        if r.status_code in (200, 201):
            data = r.json()
            return {"success": True, "result": data.get("data", data), "error": None}
        try:
            err_data = r.json()
            msg = err_data.get("message", err_data.get("exc", str(err_data)))
        except Exception:
            msg = r.text or f"HTTP {r.status_code}"
        return {"success": False, "result": None, "error": msg}
    except httpx.TimeoutException:
        return {"success": False, "result": None, "error": "Request timed out"}
    except Exception as e:
        return {"success": False, "result": None, "error": str(e)}
