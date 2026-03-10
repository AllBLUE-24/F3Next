"""Payload Generator: Map entities + context → ERPNext API payload."""
from datetime import datetime
from typing import Any


def build_sales_order_payload(clarity_output: dict, context: dict) -> dict[str, Any]:
    """
    Build ERPNext Sales Order payload from Clarity output + context.
    """
    entities = clarity_output.get("entities", {})
    resolved_customer = context.get("resolved_customer", "")
    resolved_items = context.get("resolved_items", [])
    defaults = context.get("defaults", {})

    today = datetime.now().strftime("%Y-%m-%d")

    items = []
    entity_items = entities.get("items", [])
    for i, it in enumerate(resolved_items):
        rate = it.get("rate")
        if rate is None and i < len(entity_items):
            rate = entity_items[i].get("rate") or entity_items[i].get("price")
        row = {
            "item_code": it.get("item_code", ""),
            "qty": it.get("qty", 0),
            "rate": rate,
        }
        if defaults.get("warehouse"):
            row["warehouse"] = defaults["warehouse"]
        items.append(row)

    payload = {
        "doctype": "Sales Order",
        "customer": resolved_customer,
        "transaction_date": today,
        "delivery_date": defaults.get("delivery_date", today),
        "items": items,
    }

    if context.get("config", {}).get("company"):
        payload["company"] = context["config"]["company"]

    return payload
