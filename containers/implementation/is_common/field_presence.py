"""Shared required-field presence checks for mapped ERPNext rows (preflight + validate)."""
from __future__ import annotations

from typing import Any, Dict, List

_ITEM_CHILD_KEYS = frozenset({"item_code", "qty", "rate", "uom", "warehouse"})


def _non_empty(val: Any) -> bool:
    if val is None:
        return False
    if isinstance(val, str):
        return bool(val.strip())
    if isinstance(val, list):
        return len(val) > 0
    return True


def _items_populated(row: Dict[str, Any]) -> bool:
    items = row.get("items")
    if isinstance(items, list):
        for child in items:
            if not isinstance(child, dict):
                continue
            code = child.get("item_code") or child.get("item_name")
            if _non_empty(code):
                return True
        return False

    for key, val in row.items():
        k = str(key)
        if k.startswith("items.") and _non_empty(val):
            return True
        if k in _ITEM_CHILD_KEYS and _non_empty(val):
            return True
    return False


def field_present_in_mapped_row(field: str, row: Dict[str, Any]) -> bool:
    """True when a required field has a usable value on a mapped record."""
    if not isinstance(row, dict):
        return False

    if field == "items":
        return _items_populated(row)

    if field in row:
        return _non_empty(row.get(field))

    # Namespaced child keys (pre-fold): e.g. items.item_code
    prefix = f"{field}."
    for key, val in row.items():
        if str(key).startswith(prefix) and _non_empty(val):
            return True

    return False


def missing_required_on_records(
    doctype: str,
    records: List[Dict[str, Any]],
    required: List[str],
) -> List[str]:
    """Return required field names absent from all sample records."""
    sample = [r for r in records[:10] if isinstance(r, dict)]
    if not sample or not required:
        return []

    missing: List[str] = []
    for field in required:
        if not any(field_present_in_mapped_row(field, row) for row in sample):
            missing.append(field)
    return missing
