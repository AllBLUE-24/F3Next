"""Field-level import policy for data readiness (defaultable vs must-ask)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

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

# Identity field — must be derivable from file or user must provide
_IDENTITY_FIELD: Dict[str, str] = {
    "Customer": "customer_name",
    "Supplier": "supplier_name",
    "Item": "item_code",
    "Project": "project_name",
    "Employee": "employee_name",
}

# Column → ERP identity (derivation hints for readiness)
_IDENTITY_COLUMN_HINTS: Dict[str, List[str]] = {
    "customer_name": ["company_name", "company name", "client", "client_name", "party_name", "name"],
    "supplier_name": ["company_name", "company name", "vendor_name", "vendor name", "party_name", "name"],
    "item_code": ["product", "item", "item_code", "item code", "sku", "material", "fg_item"],
    "project_name": ["project", "project_name", "project name", "client"],
}


def _kb_default(doctype: str, field: str, kb: Dict[str, Any]) -> Optional[Any]:
    dt_cfg = (kb.get("doctypes") or {}).get(doctype) or {}
    fmap = dt_cfg.get("field_mappings") or {}
    for _, cfg in fmap.items():
        if cfg.get("fieldname") == field:
            dval = cfg.get("default_value")
            if dval and dval not in ("today",) and "user_default" not in str(dval):
                return dval
    return _DOCTYPE_DEFAULTS.get(doctype, {}).get(field)


def resolve_default(doctype: str, field: str, kb: Dict[str, Any]) -> Optional[Any]:
    """Return safe import default for a field, if one exists."""
    return _kb_default(doctype, field, kb)


def classify_missing_fields(
    doctype: str,
    missing_fields: List[str],
    matched_fields: List[str],
    kb: Dict[str, Any],
) -> Tuple[List[Dict[str, Any]], List[str], List[str]]:
    """
    Split missing mandatory fields into assumptions (defaults) vs must-ask.

    Returns: (assumed_fields, defaultable_names, must_ask_names)
    """
    assumed: List[Dict[str, Any]] = []
    must_ask: List[str] = []

    for field in missing_fields:
        default_val = resolve_default(doctype, field, kb)
        if default_val is not None:
            assumed.append({
                "field": field,
                "value": default_val,
                "reason": "ERPNext/KB default will be applied at mapping",
            })
        else:
            must_ask.append(field)

    return assumed, [a["field"] for a in assumed], must_ask


def identity_satisfied(
    doctype: str,
    matched_fields: List[str],
    columns: List[str],
    *,
    party_row_count: int = 0,
    corpus_hit: bool = False,
) -> bool:
    """True when the doctype has enough identity signal to proceed with defaults."""
    identity = _IDENTITY_FIELD.get(doctype)
    if identity and identity in matched_fields:
        return True
    if party_row_count > 0:
        return True
    if corpus_hit:
        return True
    cols = {_norm_col(c) for c in columns}
    hints = _IDENTITY_COLUMN_HINTS.get(identity or "", [])
    for hint in hints:
        h = _norm_col(hint)
        for col in cols:
            if col == h or (len(h) >= 3 and h in col):
                return True
    return False


def _norm_col(s: str) -> str:
    return str(s or "").strip().lower().replace("_", " ")
