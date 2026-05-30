"""
LER-backed ERP read helpers for tool loops and execution preflight.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from shared.erp_adapters.base import ERPAdapter

logger = logging.getLogger(__name__)


async def list_master(
    adapter: ERPAdapter,
    doctype: str,
    *,
    query: Optional[str] = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """
    Top N master records from live ERP (``name`` field always included).
    """
    fields = ["name"]
    filters: list[list[Any]] | None = None
    if query and query.strip():
        filters = [["name", "like", f"%{query.strip()}%"]]

    try:
        records = await adapter.list_records(
            doctype,
            fields,
            filters=filters,
            limit=min(max(limit, 1), 200),
        )
    except Exception as e:
        logger.warning("list_master failed for %s: %s", doctype, e)
        return []

    return [r for r in records if r.get("name")]


async def get_item_flags(
    adapter: ERPAdapter,
    item_code: str,
) -> dict[str, Any]:
    """Flags needed for PO/SO preflight (subcontract, stock, UOM)."""
    code = str(item_code or "").strip()
    if not code:
        return {}
    try:
        doc = await adapter.get_record("Item", code)
    except Exception as e:
        logger.warning("get_item_flags failed for %s: %s", code, e)
        return {"item_code": code, "_error": str(e)}

    if not doc:
        return {"item_code": code, "_missing": True}

    return {
        "item_code": code,
        "name": doc.get("name"),
        "is_sub_contracted_item": bool(doc.get("is_sub_contracted_item")),
        "is_stock_item": doc.get("is_stock_item"),
        "stock_uom": doc.get("stock_uom"),
        "item_group": doc.get("item_group"),
    }


async def get_supplier_flags(
    adapter: ERPAdapter,
    supplier: str,
) -> dict[str, Any]:
    """Supplier flags for subcontract PO preflight."""
    name = str(supplier or "").strip()
    if not name:
        return {}
    try:
        doc = await adapter.get_record("Supplier", name)
    except Exception as e:
        logger.warning("get_supplier_flags failed for %s: %s", name, e)
        return {"supplier": name, "_error": str(e)}

    if not doc:
        return {"supplier": name, "_missing": True}

    return {
        "supplier": name,
        "name": doc.get("name"),
        "is_sub_contractor": bool(doc.get("is_sub_contractor")),
        "supplier_group": doc.get("supplier_group"),
    }
