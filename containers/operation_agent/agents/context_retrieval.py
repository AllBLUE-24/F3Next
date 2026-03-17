"""Context Retrieval: Load config, schema, resolve customer/item via ERPNext API."""
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

from config import (
    DOCTYPE_GRAPH_PATH,
    ERPNEXT_COMPANY,
    ERPNEXT_URL,
    get_erpnext_auth,
)


def load_doctype_graph() -> dict:
    """Load doctype graph from knowledge base."""
    with open(DOCTYPE_GRAPH_PATH, encoding="utf-8") as f:
        return json.load(f)


def get_sales_order_schema() -> dict:
    """Get Sales Order schema from doctype graph."""
    graph = load_doctype_graph()
    doctypes = graph.get("doctypes", {})
    so = doctypes.get("Sales Order", {})
    return {
        "required_fields": so.get("required_fields", ["customer", "items", "delivery_date"]),
        "doctype": "Sales Order",
    }


def lookup_customer(name: str) -> str | None:
    """Look up customer by name in ERPNext. Returns customer_id (name) or None."""
    if not ERPNEXT_URL:
        return name  # No ERP, skip lookup
    api_key, api_secret = get_erpnext_auth()
    if not api_key or not api_secret:
        return name
    url = f"{ERPNEXT_URL}/api/resource/Customer"
    auth = (api_key, api_secret)
    params = {"filters": json.dumps([["customer_name", "like", f"%{name}%"]]), "limit_page_length": 1}
    try:
        r = httpx.get(url, auth=auth, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        entries = data.get("data", [])
        if entries:
            return entries[0].get("name")
    except Exception:
        pass
    return name


def lookup_item(name: str) -> str | None:
    """Look up item by name/code in ERPNext. Returns item_code or None."""
    if not ERPNEXT_URL:
        return name
    api_key, api_secret = get_erpnext_auth()
    if not api_key or not api_secret:
        return name
    url = f"{ERPNEXT_URL}/api/resource/Item"
    auth = (api_key, api_secret)
    params = {"filters": json.dumps([["item_name", "like", f"%{name}%"]]), "limit_page_length": 1}
    try:
        r = httpx.get(url, auth=auth, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        entries = data.get("data", [])
        if entries:
            return entries[0].get("item_code") or entries[0].get("name")
        # Try exact item_code match
        params = {"filters": json.dumps([["item_code", "=", name]]), "limit_page_length": 1}
        r = httpx.get(url, auth=auth, params=params, timeout=10)
        r.raise_for_status()
        entries = r.json().get("data", [])
        if entries:
            return entries[0].get("item_code")
    except Exception:
        pass
    return name


def get_default_warehouse() -> str | None:
    """Get default warehouse from ERPNext if available."""
    if not ERPNEXT_URL:
        return None
    api_key, api_secret = get_erpnext_auth()
    if not api_key or not api_secret:
        return None
    try:
        r = httpx.get(f"{ERPNEXT_URL}/api/resource/Warehouse", auth=(api_key, api_secret), params={"limit_page_length": 1}, timeout=5)
        r.raise_for_status()
        entries = r.json().get("data", [])
        if entries:
            return entries[0].get("name")
    except Exception:
        pass
    return None


def get_context(intent: str, entities: dict) -> dict[str, Any]:
    """
    Build context bundle for create_sales_order.
    Returns: config, schema, resolved customer, resolved items, defaults.
    """
    schema = get_sales_order_schema()
    customer_name = entities.get("customer", "")
    items = entities.get("items", [])

    resolved_customer = lookup_customer(customer_name) if customer_name else None
    resolved_items = []
    for it in items:
        item_name = it.get("item", "")
        resolved_code = lookup_item(item_name) if item_name else None
        resolved_items.append({
            "item_code": resolved_code or item_name,
            "qty": it.get("qty", 0),
            "rate": it.get("rate") or it.get("price"),
        })

    default_warehouse = get_default_warehouse()
    today = datetime.now().strftime("%Y-%m-%d")

    return {
        "config": {
            "erp_url": ERPNEXT_URL,
            "company": ERPNEXT_COMPANY,
        },
        "schema": schema,
        "resolved_customer": resolved_customer or customer_name,
        "resolved_items": resolved_items,
        "defaults": {
            "transaction_date": today,
            "delivery_date": today,
            "warehouse": default_warehouse,
        },
    }
