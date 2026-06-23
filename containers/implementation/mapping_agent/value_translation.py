"""Value Translation Layer (VTL) — cell-value normalization after column mapping."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set, Tuple

from containers.knowledge_base.erpnext.schema.compose import compose_value_translation


def _norm(s: Any) -> str:
    return re.sub(r"\s+", " ", str(s or "").strip().lower())


def _party_ledger_values(vtl: Dict[str, Any]) -> Set[str]:
    policies = vtl.get("link_field_policies") or {}
    raw = policies.get("party_ledger_class_values") or []
    return {_norm(v) for v in raw if v}


def _field_maps_for_doctype(vtl: Dict[str, Any], doctype: str) -> Dict[str, Dict[str, str]]:
    """Merge baseline + source-system field_value_maps for a doctype."""
    out: Dict[str, Dict[str, str]] = {}
    baseline = (vtl.get("erpnext_baseline") or {}).get("field_value_maps") or {}
    tally = (vtl.get("tally") or {}).get("field_value_maps") or {}
    for src in (baseline, tally):
        dt_maps = src.get(doctype) or {}
        if not isinstance(dt_maps, dict):
            continue
        for field, mapping in dt_maps.items():
            if not isinstance(mapping, dict):
                continue
            bucket = out.setdefault(str(field), {})
            for raw_val, target in mapping.items():
                if raw_val and target:
                    bucket[str(raw_val)] = str(target)
    return out


def _resolve_mapped_value(field: str, value: Any, field_maps: Dict[str, Dict[str, str]]) -> Optional[str]:
    if value in (None, ""):
        return None
    mapping = field_maps.get(field) or {}
    if not mapping:
        return None
    raw = str(value).strip()
    if raw in mapping:
        return mapping[raw]
    lowered = raw.lower()
    for k, v in mapping.items():
        if str(k).lower() == lowered:
            return v
    return None


def _baseline_default_for_field(
    doctype: str,
    field: str,
    vtl: Dict[str, Any],
    *,
    context: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    policies = (vtl.get("link_field_policies") or {}).get("field_policies") or {}
    dt_pol = (policies.get(doctype) or {}).get(field) or {}
    if not isinstance(dt_pol, dict):
        return None
    baseline = dt_pol.get("baseline_default")
    if baseline:
        return str(baseline)
    ctx_key = dt_pol.get("default_field") or field
    ctx_val = (context or {}).get(ctx_key)
    if ctx_val:
        return str(ctx_val)
    return None


def _is_party_ledger_value(value: Any, ledger_values: Set[str]) -> bool:
    return _norm(value) in ledger_values


def apply_value_translations(
    doctype: str,
    records: List[Dict[str, Any]],
    *,
    context: Optional[Dict[str, Any]] = None,
    overwrite: bool = False,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Apply VTL policies to mapped records.

    Returns (records, audit) where audit entries are
    {field, from, to, rule_id}.
    """
    if not records:
        return records, []

    vtl = compose_value_translation()
    field_maps = _field_maps_for_doctype(vtl, doctype)
    ledger_values = _party_ledger_values(vtl)
    field_policies = (vtl.get("link_field_policies") or {}).get("field_policies") or {}
    dt_policies = field_policies.get(doctype) or {}

    audit: List[Dict[str, Any]] = []
    out: List[Dict[str, Any]] = []

    for rec in records:
        r = dict(rec)
        for field, pol in dt_policies.items():
            if not isinstance(pol, dict):
                continue
            if pol.get("policy") != "drop_party_ledger_use_default":
                continue
            current = r.get(field)
            if current in (None, "") and not overwrite:
                continue
            if current not in (None, "") and not _is_party_ledger_value(current, ledger_values):
                continue
            default_val = _baseline_default_for_field(doctype, field, vtl, context=context)
            if default_val is None:
                continue
            if current == default_val:
                continue
            audit.append({
                "field": field,
                "from": current,
                "to": default_val,
                "rule_id": "vtl_drop_party_ledger",
            })
            r[field] = default_val

        for field, _mapping in field_maps.items():
            current = r.get(field)
            if current in (None, ""):
                continue
            translated = _resolve_mapped_value(field, current, field_maps)
            if not translated or translated == current:
                continue
            audit.append({
                "field": field,
                "from": current,
                "to": translated,
                "rule_id": "vtl_field_value_map",
            })
            r[field] = translated

        out.append(r)

    return out, audit


def normalize_mapped_payload(
    doctype: str,
    payload: Dict[str, Any],
    *,
    context: Optional[Dict[str, Any]] = None,
    overwrite: bool = False,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    if not isinstance(payload, dict):
        return payload, []
    records = payload.get("records")
    if not isinstance(records, list):
        return payload, []
    translated, audit = apply_value_translations(
        doctype, records, context=context, overwrite=overwrite
    )
    out = dict(payload)
    out["records"] = translated
    return out, audit
