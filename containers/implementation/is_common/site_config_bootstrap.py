"""Site Config Bootstrap (SCB) — derive missing config masters from mapped payloads."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set, Tuple

from containers.implementation.mapping_agent.value_translation import (
    apply_value_translations,
    fuzzy_match_live_erp,
)
from shared.entity_resolution.gaps import _fuzzy_candidates

_CONFIG_LINK_FIELDS: Tuple[Tuple[str, str, str], ...] = (
    ("Item", "item_group", "Item Group"),
    ("Customer", "customer_group", "Customer Group"),
    ("Supplier", "supplier_group", "Supplier Group"),
    ("Customer", "territory", "Territory"),
    ("Item", "stock_uom", "UOM"),
    ("Item", "uom", "UOM"),
)

_CONFIG_NAME_FIELDS: Dict[str, str] = {
    "Item Group": "item_group_name",
    "Customer Group": "customer_group_name",
    "Supplier Group": "supplier_group_name",
    "Territory": "territory_name",
    "UOM": "uom_name",
}

_PHASE_0_ORDER: Tuple[str, ...] = (
    "UOM",
    "Item Group",
    "Customer Group",
    "Supplier Group",
    "Territory",
)


def _norm(s: Any) -> str:
    return re.sub(r"\s+", " ", str(s or "").strip().lower())


def collect_distinct_link_values(
    mapped_data: Dict[str, Any],
) -> Dict[str, Set[str]]:
    """Return {config_doctype: {distinct raw values}} from mapped master rows."""
    out: Dict[str, Set[str]] = {}
    for source_dt, field, config_dt in _CONFIG_LINK_FIELDS:
        payload = mapped_data.get(source_dt) or {}
        records = payload.get("records") or []
        if not isinstance(records, list):
            continue
        bucket = out.setdefault(config_dt, set())
        for rec in records:
            if not isinstance(rec, dict):
                continue
            val = rec.get(field)
            if val not in (None, ""):
                bucket.add(str(val).strip())
    return out


def values_covered_by_bootstrap(
    mapped_data: Dict[str, Any],
    *,
    config_doctype: str,
    value: str,
) -> bool:
    """True when SCB already derived a config master row for this value."""
    payload = mapped_data.get(config_doctype) or {}
    records = payload.get("records") or []
    if not isinstance(records, list):
        return False
    name_field = _CONFIG_NAME_FIELDS.get(config_doctype, "name")
    needle = _norm(value)
    for rec in records:
        if not isinstance(rec, dict):
            continue
        candidate = rec.get(name_field) or rec.get("name")
        if _norm(candidate) == needle:
            return True
    return False


def resolve_config_value(
    raw_value: str,
    *,
    config_doctype: str,
    link_cache: Optional[Dict[str, List[str]]] = None,
) -> Tuple[str, str]:
    """
    Resolve a config link value via live ERP fuzzy match.

    Returns (resolved_value, rule_id) where rule_id is one of:
    live_erp_exact, live_erp_fuzzy, unchanged.
    """
    val = str(raw_value or "").strip()
    if not val:
        return val, "unchanged"

    known = list(link_cache.get(config_doctype) or []) if link_cache else []
    if not known:
        return val, "unchanged"

    for name in known:
        if _norm(name) == _norm(val):
            return name, "live_erp_exact"

    fuzzy = fuzzy_match_live_erp(val, known)
    if fuzzy:
        return fuzzy, "live_erp_fuzzy"

    candidates = _fuzzy_candidates(val, known, limit=1)
    if len(candidates) == 1:
        return candidates[0], "live_erp_fuzzy"

    return val, "unchanged"


def patch_mapped_payloads_with_live_fuzzy(
    mapped_data: Dict[str, Any],
    link_cache: Optional[Dict[str, List[str]]] = None,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Apply VTL + live ERP fuzzy match to mapped master payloads."""
    out = dict(mapped_data)
    audit: List[Dict[str, Any]] = []

    for source_dt, field, config_dt in _CONFIG_LINK_FIELDS:
        payload = out.get(source_dt)
        if not isinstance(payload, dict):
            continue
        records = payload.get("records")
        if not isinstance(records, list) or not records:
            continue

        translated, vtl_audit = apply_value_translations(
            source_dt,
            records,
            overwrite=False,
            link_cache=link_cache,
        )
        patched = list(translated)
        for idx, rec in enumerate(patched):
            if not isinstance(rec, dict):
                continue
            current = rec.get(field)
            if current in (None, ""):
                continue
            resolved, rule_id = resolve_config_value(
                str(current),
                config_doctype=config_dt,
                link_cache=link_cache,
            )
            if resolved and resolved != current:
                audit.append({
                    "doctype": source_dt,
                    "field": field,
                    "from": current,
                    "to": resolved,
                    "rule_id": rule_id,
                })
                patched[idx] = {**rec, field: resolved}

        out[source_dt] = {**payload, "records": patched}
        audit.extend({"doctype": source_dt, **a} for a in vtl_audit)

    return out, audit


def derive_config_records(
    mapped_data: Dict[str, Any],
    *,
    link_cache: Optional[Dict[str, List[str]]] = None,
) -> Tuple[Dict[str, Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Build config master payloads for values still missing on live ERP.

    Returns ({config_doctype: payload}, audit).
    """
    distinct = collect_distinct_link_values(mapped_data)
    derived: Dict[str, Dict[str, Any]] = {}
    audit: List[Dict[str, Any]] = []

    known_sets: Dict[str, Set[str]] = {}
    if link_cache:
        for dt, names in link_cache.items():
            known_sets[dt] = {_norm(n) for n in (names or [])}

    for config_dt, values in distinct.items():
        if not values:
            continue
        name_field = _CONFIG_NAME_FIELDS.get(config_dt, "name")
        records: List[Dict[str, Any]] = []
        existing = mapped_data.get(config_dt) or {}
        if isinstance(existing, dict):
            for rec in existing.get("records") or []:
                if isinstance(rec, dict):
                    records.append(dict(rec))

        seen_names = {
            _norm(r.get(name_field) or r.get("name"))
            for r in records
            if isinstance(r, dict)
        }

        for raw in sorted(values):
            resolved, rule_id = resolve_config_value(
                raw,
                config_doctype=config_dt,
                link_cache=link_cache,
            )
            if rule_id != "unchanged":
                continue
            if _norm(resolved) in (known_sets.get(config_dt) or set()):
                continue
            if _norm(resolved) in seen_names:
                continue

            records.append({name_field: resolved})
            seen_names.add(_norm(resolved))
            audit.append({
                "config_doctype": config_dt,
                "value": resolved,
                "rule_id": "scb_derive_config",
            })

        if records:
            derived[config_dt] = {
                "records": records,
                "source": "site_config_bootstrap",
                "total_rows": len(records),
            }

    return derived, audit


def bootstrap_site_config(
    mapped_data: Dict[str, Any],
    *,
    link_cache: Optional[Dict[str, List[str]]] = None,
) -> Dict[str, Any]:
    """
    Full SCB pass: fuzzy-patch masters, derive missing config rows.

    Returns summary with patched mapped_data, derived payloads, and audit trail.
    """
    patched_data, patch_audit = patch_mapped_payloads_with_live_fuzzy(
        mapped_data, link_cache=link_cache,
    )
    derived, derive_audit = derive_config_records(
        patched_data, link_cache=link_cache,
    )

    merged = dict(patched_data)
    for dt, payload in derived.items():
        merged[dt] = payload

    return {
        "mapped_data": merged,
        "derived_config": derived,
        "patch_audit": patch_audit,
        "derive_audit": derive_audit,
        "derived_doctypes": sorted(derived.keys()),
    }


def phase_0_steps_from_bootstrap(
    derived_config: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Build import plan steps for Phase 0 site config bootstrap."""
    steps: List[Dict[str, Any]] = []
    step_num = 1
    for dt in _PHASE_0_ORDER:
        payload = derived_config.get(dt)
        if not payload:
            continue
        count = len(payload.get("records") or [])
        if not count:
            continue
        steps.append({
            "step": step_num,
            "doctype": dt,
            "action": "create",
            "data_source": "site_config_bootstrap",
            "records": count,
        })
        step_num += 1
    return steps
