"""Field-level import policy for data readiness (defaultable vs blocking)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from containers.implementation.is_common.required_fields import get_required_fields

# Mirrors mapping_agent/defaults.py hardcoded fallbacks + field_mappings default_value
_DOCTYPE_DEFAULTS: Dict[str, Dict[str, Any]] = {
    "Customer": {
        "customer_type": "Company",
        "customer_group": "All Customer Groups",
        "territory": "All Territories",
    },
    "Supplier": {
        "supplier_type": "Company",
        "supplier_group": "All Supplier Groups",
    },
    "Item": {
        "item_group": "Consumable",
        "stock_uom": "Nos",
    },
}

# Relative defaults resolved at mapping when parent field exists
_RELATIVE_DEFAULT_PARENT: Dict[str, str] = {
    "delivery_date": "transaction_date",
    "schedule_date": "transaction_date",
}

_IDENTITY_FIELD: Dict[str, str] = {
    "Customer": "customer_name",
    "Supplier": "supplier_name",
    "Item": "item_code",
    "Project": "project_name",
    "Employee": "employee_name",
}

# Structural / aggregate hints not expressed as a single KB field synonym list.
_STRUCTURAL_COLUMN_HINTS: Dict[str, List[str]] = {
    "items": ["product", "item", "sku", "material", "ordered_qty", "vol", "qty", "price"],
    "item_name": ["product", "item", "item_code", "item code", "sku", "material"],
}


def _kb_column_hints(kb: Dict[str, Any]) -> Dict[str, List[str]]:
    """Derive column hints from KB field_mappings + child_fields."""
    hints: Dict[str, set] = {}
    for dt_cfg in (kb.get("doctypes") or {}).values():
        fmap = dt_cfg.get("field_mappings") or {}
        for fn, cfg in fmap.items():
            field = str(cfg.get("fieldname") or fn)
            syns = list(cfg.get("user_input_synonyms") or []) + [field, fn]
            bucket = hints.setdefault(field, set())
            bucket.update(_norm_col(s) for s in syns if s)
            for child_cfg in (cfg.get("child_fields") or {}).values():
                if not isinstance(child_cfg, dict):
                    continue
                cf = str(child_cfg.get("fieldname") or "")
                if not cf:
                    continue
                child_syns = list(child_cfg.get("user_input_synonyms") or []) + [cf]
                child_bucket = hints.setdefault(cf, set())
                child_bucket.update(_norm_col(s) for s in child_syns if s)
    return {k: sorted(v) for k, v in hints.items()}


def _column_hints_for_field(field: str, kb: Dict[str, Any]) -> List[str]:
    kb_hints = _kb_column_hints(kb)
    hints = list(kb_hints.get(field, []))
    hints.extend(_STRUCTURAL_COLUMN_HINTS.get(field, []))
    hints.append(_norm_col(field))
    return list(dict.fromkeys(hints))

_ITEM_CHILD_MATCHED = frozenset({"item_code", "qty", "rate", "uom"})


def _kb_default(doctype: str, field: str, kb: Dict[str, Any]) -> Optional[Any]:
    dt_cfg = (kb.get("doctypes") or {}).get(doctype) or {}
    if field == "naming_series":
        ns = dt_cfg.get("naming_series")
        if ns:
            return ns
    fmap = dt_cfg.get("field_mappings") or {}
    for _, cfg in fmap.items():
        if cfg.get("fieldname") == field:
            dval = cfg.get("default_value")
            if dval in ("today", "now", "Today"):
                return dval
            dval_s = str(dval or "").lower()
            if dval and ("user_default" in dval_s or "first company" in dval_s):
                return dval
            if dval and "+" not in str(dval):
                return dval
            if dval and "+" in str(dval) and _RELATIVE_DEFAULT_PARENT.get(field):
                return "__relative_default__"
    global_rules = kb.get("default_value_rules") or {}
    if field in global_rules:
        return global_rules[field]
    return _DOCTYPE_DEFAULTS.get(doctype, {}).get(field)


def resolve_default(doctype: str, field: str, kb: Dict[str, Any]) -> Optional[Any]:
    """Return safe import default for a field, if one exists."""
    return _kb_default(doctype, field, kb)


def _column_covers_field(field: str, columns: List[str], kb: Optional[Dict[str, Any]] = None) -> bool:
    cols = {_norm_col(c) for c in columns}
    hints = _column_hints_for_field(field, kb or {})
    for hint in hints:
        h = _norm_col(hint)
        for col in cols:
            if col == h or (len(h) >= 3 and h in col):
                return True
    if field == "item_name" and _column_covers_field("item_code", columns, kb):
        return True
    return False


def _matched_covers_field(field: str, matched_fields: List[str]) -> bool:
    if field in matched_fields:
        return True
    if field == "items":
        return any(
            m.startswith("items.") or m.split(".")[-1] in _ITEM_CHILD_MATCHED
            for m in matched_fields
        )
    if field == "item_name" and "item_code" in matched_fields:
        return True
    return False


def classify_missing_fields(
    doctype: str,
    missing_fields: List[str],
    matched_fields: List[str],
    kb: Dict[str, Any],
    *,
    columns: Optional[List[str]] = None,
    f3iche_id: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], List[str], List[str]]:
    """
    Split missing required fields into assumptions (defaults) vs blocking must-ask.

    Returns: (assumed_fields, defaultable_names, blocking_names)
    """
    from containers.implementation.is_common.f3iche_policy import (
        always_ask_fields,
        deferred_fields,
        f3iche_default_for,
        is_deferred_doctype,
        must_ask_for_doctype,
    )

    assumed: List[Dict[str, Any]] = []
    blocking: List[str] = []
    cols = columns or []

    if f3iche_id and is_deferred_doctype(doctype, f3iche_id):
        return assumed, [], []

    if f3iche_id and must_ask_for_doctype(doctype, f3iche_id):
        return assumed, [], list(missing_fields)

    must_ask_fields = always_ask_fields(f3iche_id or "")
    post_mvp_fields = deferred_fields(f3iche_id or "")
    for field in missing_fields:
        if field in matched_fields:
            continue
        if field in post_mvp_fields:
            continue
        if field in must_ask_fields:
            blocking.append(field)
            continue
        if cols and _column_covers_field(field, cols, kb):
            assumed.append({
                "field": field,
                "value": "(from uploaded column)",
                "reason": "Column signal present — LLM/KB mapping will apply at Step 9",
            })
            continue
        default_val = None
        if f3iche_id:
            default_val = f3iche_default_for(doctype, field, f3iche_id)
        if default_val is None:
            default_val = resolve_default(doctype, field, kb)
        if default_val == "__relative_default__":
            parent = _RELATIVE_DEFAULT_PARENT.get(field, "")
            if parent in matched_fields or _column_covers_field(parent, cols, kb):
                assumed.append({
                    "field": field,
                    "value": f"derived from {parent}",
                    "reason": "Relative default will be applied at mapping",
                })
            else:
                blocking.append(field)
            continue
        if default_val is not None:
            assumed.append({
                "field": field,
                "value": default_val,
                "reason": "ERPNext/KB default will be applied at mapping",
            })
        else:
            blocking.append(field)

    return assumed, [a["field"] for a in assumed], blocking


def identity_satisfied(
    doctype: str,
    matched_fields: List[str],
    columns: List[str],
    kb: Optional[Dict[str, Any]] = None,
) -> bool:
    """True when identity/required link fields are derivable from columns or matches."""
    identity = _IDENTITY_FIELD.get(doctype)
    if identity and identity in matched_fields:
        return True
    kb = kb or {}
    if identity and _column_covers_field(identity, columns, kb):
        return True
    return False


def assess_field_coverage(
    doctype: str,
    matched_fields: List[str],
    columns: List[str],
    kb: Dict[str, Any],
    *,
    f3iche_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Field-level coverage using graph required_fields (same as validate)."""
    required = get_required_fields(doctype)
    missing = [f for f in required if not _matched_covers_field(f, matched_fields)]
    assumed, _, blocking = classify_missing_fields(
        doctype, missing, matched_fields, kb, columns=columns, f3iche_id=f3iche_id,
    )
    can_proceed = len(blocking) == 0
    return {
        "required_fields": required,
        "matched_fields": matched_fields,
        "assumed_fields": assumed,
        "blocking_fields": blocking,
        "can_proceed_without": can_proceed,
        "assumption_only": bool(assumed) and can_proceed,
        "ready_with_assumptions": bool(assumed) and can_proceed,
    }


def _norm_col(s: str) -> str:
    return str(s or "").strip().lower().replace("_", " ")
