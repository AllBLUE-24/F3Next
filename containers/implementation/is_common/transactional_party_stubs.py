"""Derive Customer/Supplier master stubs from transactional party references."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

from containers.implementation.is_common.ler_greenfield import batch_identity_values

_RULES: List[Tuple[str, str, str, str]] = [
    ("Sales Order", "customer", "Customer", "customer_name"),
    ("Purchase Order", "supplier", "Supplier", "supplier_name"),
]

_STUB_DEFAULTS: Dict[str, Dict[str, Any]] = {
    "Customer": {
        "customer_type": "Company",
        "customer_group": "All Customer Groups",
        "territory": "All Territories",
    },
    "Supplier": {
        "supplier_type": "Company",
        "supplier_group": "All Supplier Groups",
    },
}


def _norm(s: Any) -> str:
    return re.sub(r"\s+", " ", str(s or "").strip().lower())


def _collect_refs(mapped_data: Dict[str, Any], src_dt: str, ref_field: str) -> List[str]:
    payload = mapped_data.get(src_dt) or {}
    records = payload.get("records") or []
    if not isinstance(records, list):
        return []
    refs: List[str] = []
    seen: set[str] = set()
    for rec in records:
        if not isinstance(rec, dict):
            continue
        val = rec.get(ref_field)
        if val in (None, ""):
            continue
        key = _norm(val)
        if key and key not in seen:
            seen.add(key)
            refs.append(str(val).strip())
    return refs


def derive_transactional_party_masters(
    mapped_data: Dict[str, Any],
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Add master records for parties referenced on SO/PO rows but missing from master payloads.

    Returns (updated_mapped_data, stub_audit_entries).
    """
    updated = dict(mapped_data)
    audit: List[Dict[str, Any]] = []

    for src_dt, ref_field, master_dt, identity_field in _RULES:
        refs = _collect_refs(updated, src_dt, ref_field)
        if not refs:
            continue

        existing_identities = batch_identity_values(updated, master_dt)
        master_payload = dict(updated.get(master_dt) or {})
        master_records = list(master_payload.get("records") or [])
        known = {_norm(r.get(identity_field)) for r in master_records if isinstance(r, dict)}

        added: List[Dict[str, Any]] = []
        for name in refs:
            needle = _norm(name)
            if not needle or needle in known or needle in existing_identities:
                continue
            stub = {identity_field: name, **_STUB_DEFAULTS.get(master_dt, {})}
            master_records.append(stub)
            known.add(needle)
            added.append(stub)

        if not added:
            continue

        master_payload["records"] = master_records
        master_payload.setdefault("doctype", master_dt)
        updated[master_dt] = master_payload
        audit.append({
            "master_doctype": master_dt,
            "source_doctype": src_dt,
            "reference_field": ref_field,
            "stubs_added": len(added),
            "names": [s[identity_field] for s in added],
        })

    return updated, audit
