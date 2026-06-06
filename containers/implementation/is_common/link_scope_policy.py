"""Strip Link-field mappings when target doctype is out of MVP scope."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set, Tuple

# Link targets not mapped unless the session explicitly includes that doctype.
_DEFERRED_LINK_TARGETS = frozenset({"Contact", "Address"})

_PERSON_CONTACT_COLUMN = re.compile(r"^contact$", re.I)


def _link_target_for_field(doctype: str, field_name: str, kb: Dict[str, Any]) -> Optional[str]:
    dt_cfg = (kb.get("doctypes") or {}).get(doctype) or {}
    fmap = dt_cfg.get("field_mappings") or {}
    for _fn, cfg in fmap.items():
        erp_name = cfg.get("fieldname", _fn)
        if erp_name != field_name:
            continue
        if str(cfg.get("fieldtype") or "").strip() != "Link":
            return None
        options = cfg.get("options")
        return str(options).strip() if options else None
    return None


def filter_field_mapping(
    field_mapping: Dict[str, str],
    doctype: str,
    kb: Dict[str, Any],
    *,
    scoped_doctypes: Optional[Set[str]] = None,
) -> Tuple[Dict[str, str], List[str]]:
    """
    Remove column→field pairs that target out-of-scope Link doctypes.

    Returns (filtered_mapping, stripped_target_fields).
    """
    scope = {str(d).strip() for d in (scoped_doctypes or set()) if str(d).strip()}
    filtered: Dict[str, str] = {}
    stripped_fields: List[str] = []

    for src_col, tgt_field in field_mapping.items():
        link_target = _link_target_for_field(doctype, tgt_field, kb)

        if (
            _PERSON_CONTACT_COLUMN.match(str(src_col).strip())
            and doctype in ("Customer", "Supplier")
            and link_target == "Contact"
            and "Contact" not in scope
        ):
            stripped_fields.append(tgt_field)
            continue

        if link_target in _DEFERRED_LINK_TARGETS and link_target not in scope:
            stripped_fields.append(tgt_field)
            continue

        filtered[src_col] = tgt_field

    return filtered, stripped_fields


def strip_fields_from_records(
    records: List[Dict[str, Any]],
    field_names: List[str],
) -> List[Dict[str, Any]]:
    """Drop out-of-scope link values from mapped rows."""
    if not field_names:
        return records
    drop = set(field_names)
    out: List[Dict[str, Any]] = []
    for rec in records:
        if not isinstance(rec, dict):
            out.append(rec)
            continue
        cleaned = {k: v for k, v in rec.items() if k not in drop}
        out.append(cleaned)
    return out
