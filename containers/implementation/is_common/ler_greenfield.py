"""LER greenfield: defer live link errors when same-session mapped batch covers the master."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set

_MASTER_DOCTYPES = frozenset({"Customer", "Supplier", "Item", "Company", "Warehouse"})

_IDENTITY_FIELDS: Dict[str, List[str]] = {
    "Customer": ["customer_name", "customer"],
    "Supplier": ["supplier_name", "supplier"],
    "Item": ["item_code", "item_name"],
    "Company": ["company_name", "company"],
    "Warehouse": ["warehouse", "warehouse_name"],
}


def _norm(s: Any) -> str:
    return re.sub(r"\s+", " ", str(s or "").strip().lower())


def _collect_identity_values(records: List[Dict[str, Any]], fields: List[str]) -> Set[str]:
    values: Set[str] = set()
    for rec in records:
        if not isinstance(rec, dict):
            continue
        for f in fields:
            val = rec.get(f)
            if val not in (None, ""):
                values.add(_norm(val))
    return values


def batch_identity_values(mapped_data: Dict[str, Any], link_target: str) -> Set[str]:
    """Collect normalized identity values from same-session mapped payloads."""
    target = str(link_target or "").strip()
    if not target or target not in _MASTER_DOCTYPES:
        return set()

    payload = mapped_data.get(target) or {}
    records = payload.get("records") or payload.get("rows") or []
    if not isinstance(records, list):
        return set()

    fields = _IDENTITY_FIELDS.get(target, [])
    return _collect_identity_values(records, fields)


def session_covers_link_value(
    mapped_data: Dict[str, Any],
    *,
    link_target: str,
    value: str,
) -> bool:
    """True when mapped batch contains a master record matching the unresolved link value."""
    if not value or not link_target:
        return False
    needle = _norm(value)
    if not needle:
        return False
    identities = batch_identity_values(mapped_data, link_target)
    if needle in identities:
        return True
    # Fuzzy: uploaded name contained in link value or vice versa (party names)
    for ident in identities:
        if len(ident) >= 4 and (ident in needle or needle in ident):
            return True
    return False


def classify_ler_unresolvable(
    entry: Dict[str, Any],
    mapped_data: Dict[str, Any],
) -> tuple[str, str]:
    """
    Returns (disposition, message) where disposition is 'info' or 'blocking'.
    """
    link_target = str(
        entry.get("link_target") or entry.get("options") or entry.get("field") or ""
    ).strip()
    value = str(entry.get("value") or entry.get("raw_value") or "").strip()
    doctype = str(entry.get("doctype") or "Unknown")

    if link_target in _MASTER_DOCTYPES and session_covers_link_value(
        mapped_data, link_target=link_target, value=value
    ):
        return (
            "info",
            (
                f"{link_target} '{value}' is not on your live ERP site yet — it is in your "
                f"uploaded data and will be created during master import before "
                f"{doctype} records are imported."
            ),
        )

    return (
        "blocking",
        (
            f"{link_target} '{value}' was not found on your live ERP site."
        ),
    )
