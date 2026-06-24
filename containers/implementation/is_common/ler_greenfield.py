"""LER greenfield: defer live link errors when same-session mapped batch covers the master."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set, Tuple

_MASTER_DOCTYPES = frozenset({"Customer", "Supplier", "Item", "Company", "Warehouse", "Project"})
_CONFIG_DOCTYPES = frozenset({"Item Group", "Customer Group", "Supplier Group", "Territory", "UOM"})

# ERP field name (lowercase) → link target doctype
_FIELD_TO_DOCTYPE: Dict[str, str] = {
    "customer": "Customer",
    "supplier": "Supplier",
    "item_code": "Item",
    "item": "Item",
    "company": "Company",
    "warehouse": "Warehouse",
    "project": "Project",
}

_IDENTITY_FIELDS: Dict[str, List[str]] = {
    "Customer": ["customer_name", "customer"],
    "Supplier": ["supplier_name", "supplier"],
    "Item": ["item_code", "item_name"],
    "Company": ["company_name", "company"],
    "Warehouse": ["warehouse", "warehouse_name"],
    "Project": ["project_name", "name", "project"],
}

# Transactional payloads that imply a master will be created from the same upload wave
_TRANSACTIONAL_REF_FIELDS: Dict[str, List[Tuple[str, str]]] = {
    "Customer": [("Sales Order", "customer")],
    "Supplier": [("Purchase Order", "supplier")],
    "Project": [("Sales Order", "project"), ("Purchase Order", "project")],
    "Item": [
        ("Sales Order", "items"),
        ("Purchase Order", "items"),
    ],
}


def _norm(s: Any) -> str:
    return re.sub(r"\s+", " ", str(s or "").strip().lower())


def resolve_link_target_doctype(entry: Dict[str, Any]) -> str:
    """
    Resolve ERP doctype for a LER unresolvable hit.

    LER emits ``target_doctype``; legacy paths used field names (``customer``).
    """
    raw = (
        entry.get("target_doctype")
        or entry.get("link_target")
        or entry.get("options")
        or entry.get("field")
        or ""
    )
    key = str(raw).strip()
    if not key:
        return ""
    if key in _MASTER_DOCTYPES:
        return key
    mapped = _FIELD_TO_DOCTYPE.get(key.lower())
    if mapped:
        return mapped
    # Title-case fallback for single-token targets
    if key.lower() == key and key.isalpha():
        return key.title()
    return key


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


def _item_codes_from_child_table(records: List[Dict[str, Any]]) -> Set[str]:
    codes: Set[str] = set()
    for rec in records:
        if not isinstance(rec, dict):
            continue
        items = rec.get("items")
        if not isinstance(items, list):
            continue
        for row in items:
            if isinstance(row, dict):
                code = row.get("item_code")
                if code not in (None, ""):
                    codes.add(_norm(code))
    return codes


def batch_identity_values(mapped_data: Dict[str, Any], link_target: str) -> Set[str]:
    """Collect normalized identity values from same-session mapped master payloads."""
    target = str(link_target or "").strip()
    if not target or target not in _MASTER_DOCTYPES:
        return set()

    payload = mapped_data.get(target) or {}
    records = payload.get("records") or payload.get("rows") or []
    if not isinstance(records, list):
        return set()

    values = _collect_identity_values(records, _IDENTITY_FIELDS.get(target, []))
    if target == "Item":
        for dt in ("Sales Order", "Purchase Order"):
            txn = mapped_data.get(dt) or {}
            txn_records = txn.get("records") or []
            if isinstance(txn_records, list):
                values |= _item_codes_from_child_table(txn_records)
    return values


# Link-field names that may appear on any mapped doctype row (party-split, multi-map files)
_CORPUS_REF_FIELDS: Dict[str, List[str]] = {
    "Customer": ["customer", "customer_name", "party", "party_name"],
    "Supplier": ["supplier", "supplier_name", "party", "party_name", "vendor", "vendor_name"],
    "Project": ["project", "project_name"],
    "Item": ["item_code", "item_name"],
}


def corpus_reference_values(
    mapped_data: Dict[str, Any],
    link_target: str,
) -> Set[str]:
    """Scan all mapped payloads for values that reference a master link target."""
    fields = _CORPUS_REF_FIELDS.get(link_target, [])
    if not fields:
        return set()

    values: Set[str] = set()
    for payload in mapped_data.values():
        if not isinstance(payload, dict):
            continue
        records = payload.get("records") or payload.get("rows") or []
        if not isinstance(records, list):
            continue
        if link_target == "Item":
            values |= _item_codes_from_child_table(records)
        values |= _collect_identity_values(records, fields)
    return values


def transactional_reference_values(
    mapped_data: Dict[str, Any],
    link_target: str,
) -> Set[str]:
    """Values referenced on transactional rows (party/project/item stubs in orders)."""
    values: Set[str] = set()
    for src_dt, field in _TRANSACTIONAL_REF_FIELDS.get(link_target, []):
        payload = mapped_data.get(src_dt) or {}
        records = payload.get("records") or []
        if not isinstance(records, list):
            continue
        if field == "items":
            values |= _item_codes_from_child_table(records)
            continue
        for rec in records:
            if not isinstance(rec, dict):
                continue
            val = rec.get(field)
            if val not in (None, ""):
                values.add(_norm(val))
    return values


def session_covers_link_value(
    mapped_data: Dict[str, Any],
    *,
    link_target: str,
    value: str,
) -> bool:
    """True when mapped batch (masters or transactional refs) covers the unresolved link."""
    if not value or not link_target:
        return False
    needle = _norm(value)
    if not needle:
        return False

    identities = batch_identity_values(mapped_data, link_target)
    identities |= transactional_reference_values(mapped_data, link_target)
    identities |= corpus_reference_values(mapped_data, link_target)

    if needle in identities:
        return True
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
    link_target = resolve_link_target_doctype(entry)
    value = str(entry.get("value") or entry.get("raw_value") or "").strip()
    source_doctype = str(entry.get("doctype") or "Unknown")

    if link_target in _MASTER_DOCTYPES and session_covers_link_value(
        mapped_data, link_target=link_target, value=value
    ):
        return (
            "info",
            (
                f"{link_target} '{value}' will be created from your uploaded data during "
                f"master import, before {source_doctype} records are imported."
            ),
        )

    if link_target in _CONFIG_DOCTYPES:
        from containers.implementation.is_common.site_config_bootstrap import (
            values_covered_by_bootstrap,
        )

        if values_covered_by_bootstrap(
            mapped_data, config_doctype=link_target, value=value,
        ):
            return (
                "info",
                (
                    f"{link_target} '{value}' will be created in site config phase "
                    f"before {source_doctype} records are imported."
                ),
            )

    display = link_target or str(entry.get("field") or "link")
    return (
        "blocking",
        f"{display} '{value}' was not found on your live ERP site.",
    )
