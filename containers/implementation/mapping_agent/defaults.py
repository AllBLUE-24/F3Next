"""
Deterministic normalization + defaults injection for mapped ERPNext payloads.

No LLM calls are allowed here. Inputs are:
- KB field mappings (field_mappings.json)
- Baseline values (erpnext_deafaults_baseline.json)
- Runtime record dictionaries
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from containers.implementation.mapping_agent.kb import baseline_defaults, field_mappings


def _today() -> str:
    return date.today().isoformat()


def _is_iso_date(s: str) -> bool:
    try:
        datetime.strptime(str(s)[:10], "%Y-%m-%d")
        return True
    except Exception:
        return False


def _parse_known_date(s: str, formats: List[str]) -> Optional[str]:
    s = str(s or "").strip()
    if not s:
        return None
    # Always accept already-ISO
    if _is_iso_date(s):
        return s[:10]

    # Map KB formats to python strptime
    fmt_map = {
        "dd-mm-yyyy": "%d-%m-%Y",
        "dd/mm/yyyy": "%d/%m/%Y",
        "yyyy-mm-dd": "%Y-%m-%d",
        "dd-MMM-yyyy": "%d-%b-%Y",
    }
    for f in formats:
        py = fmt_map.get(str(f).strip())
        if not py:
            continue
        try:
            d = datetime.strptime(s[:20], py).date()
            return d.isoformat()
        except Exception:
            continue
    return None


def _resolve_relative_dates(s: str, today: date) -> Optional[str]:
    """
    Deterministic resolver for a small set of relative expressions.
    (Borrowed conceptually from OS Clarity agent; kept minimal here.)
    """
    if not s:
        return None
    text = str(s).strip().lower()
    if text in ("today",):
        return today.isoformat()
    if text in ("tomorrow",):
        return (today + timedelta(days=1)).isoformat()
    if text in ("yesterday",):
        return (today - timedelta(days=1)).isoformat()

    m = re.match(r"^in\s+(\d+)\s+days?$", text)
    if m:
        n = int(m.group(1))
        return (today + timedelta(days=n)).isoformat()

    # next <weekday>
    weekdays = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6}
    m = re.match(r"^next\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)$", text)
    if m:
        wd = weekdays[m.group(1)]
        days = (wd - today.weekday()) % 7
        if days == 0:
            days = 7
        return (today + timedelta(days=days)).isoformat()

    return None


def _coerce_number(v: Any) -> Optional[float]:
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace(",", "")
    try:
        return float(s)
    except Exception:
        return None


def _table_fields_for(doctype: str, kb: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    dt_cfg = (kb.get("doctypes") or {}).get(doctype) or {}
    fmap = dt_cfg.get("field_mappings") or {}
    out: Dict[str, Dict[str, Any]] = {}
    for _, cfg in fmap.items():
        if str(cfg.get("fieldtype") or "").strip().lower() == "table":
            fname = cfg.get("fieldname")
            if fname and "[]" not in str(fname):
                out[str(fname)] = cfg
    return out


def fold_child_tables(doctype: str, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    For structured sources that provide item-level columns at top-level,
    fold them into the correct child table arrays (e.g., items[]).

    Handles two styles produced by map_columns:
    1. Bare child fieldnames directly on the record — e.g., {"item_code": "RM-X", "qty": 5}
       (these come from synonym matching where the child fieldname was mapped directly)
    2. Namespaced keys — e.g., {"items.item_code": "RM-X", "items.qty": 5}
       (produced when map_columns matched via Pass 2 / child_fields recursion)

    Also groups records that belong to the same parent document by merging
    their child rows.
    """
    kb = field_mappings() or {}
    table_fields = _table_fields_for(doctype, kb)
    if not table_fields or not records:
        return records

    folded: List[Dict[str, Any]] = []
    for rec in records:
        r = dict(rec)
        for table_name, tcfg in table_fields.items():
            if isinstance(r.get(table_name), list):
                continue
            child_cfg = tcfg.get("child_fields") or {}
            child_fieldnames = [c.get("fieldname") for c in child_cfg.values() if isinstance(c, dict) and c.get("fieldname")]
            child_fieldnames = [str(x) for x in child_fieldnames if x]

            # If KB doesn't define child fields, do a minimal heuristic for common tables.
            if not child_fieldnames and table_name == "items":
                child_fieldnames = ["item_code", "qty", "rate", "warehouse", "uom"]

            child_row: Dict[str, Any] = {}

            # Style 1: namespaced keys like "items.item_code" produced by map_columns Pass 2.
            namespace_prefix = f"{table_name}."
            for key in list(r.keys()):
                if str(key).startswith(namespace_prefix):
                    child_field = key[len(namespace_prefix):]
                    val = r.pop(key)
                    if val not in (None, ""):
                        child_row[child_field] = val

            # Style 2: bare child fieldnames sitting directly on the record.
            # These come from synonym matching that happened to produce bare ERPNext field names.
            present = [f for f in child_fieldnames if f in r and r.get(f) not in (None, "")]
            for f in present:
                if f not in child_row:  # don't overwrite a namespace-matched value
                    child_row[f] = r.pop(f)

            if not child_row:
                # Ensure the array exists for schema compliance (defaults injection may fill later)
                r[table_name] = []
            else:
                r[table_name] = [child_row]

        folded.append(r)

    # Group by parent fields (all non-table fields) and merge child arrays.
    grouped: Dict[str, Dict[str, Any]] = {}
    for r in folded:
        key_obj = {k: v for k, v in r.items() if not isinstance(v, list)}
        key = str(sorted(key_obj.items(), key=lambda kv: kv[0]))
        if key not in grouped:
            grouped[key] = dict(r)
            continue
        base = grouped[key]
        for k, v in r.items():
            if isinstance(v, list):
                base.setdefault(k, [])
                if isinstance(base[k], list):
                    base[k].extend(v)
            else:
                # keep the first non-empty value
                if base.get(k) in (None, "") and v not in (None, ""):
                    base[k] = v
        grouped[key] = base

    return list(grouped.values())


def apply_defaults_and_normalize(doctype: str, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Deterministically:
    - normalize dates & numerics
    - ensure child tables exist
    - inject mandatory defaults from KB + baseline
    """
    kb = field_mappings() or {}
    baseline = baseline_defaults() or {}
    dt_cfg = (kb.get("doctypes") or {}).get(doctype) or {}
    fmap = dt_cfg.get("field_mappings") or {}
    date_formats = ((kb.get("date_parsing_rules") or {}).get("formats") or []) if kb else []

    table_fields = _table_fields_for(doctype, kb)

    out: List[Dict[str, Any]] = []
    for rec in records or []:
        r = dict(rec)

        # Ensure child tables exist
        for tname in table_fields.keys():
            if tname not in r or r[tname] is None:
                r[tname] = []

        # Normalize scalar types (dates/numbers)
        for _, cfg in fmap.items():
            fname = cfg.get("fieldname")
            if not fname or "[]" in str(fname):
                continue
            if fname not in r or r.get(fname) in (None, ""):
                continue

            ftype = str(cfg.get("fieldtype") or "").strip().lower()
            val = r.get(fname)

            if ftype == "date":
                # Resolve relative -> known formats -> keep as-is
                resolved = _resolve_relative_dates(str(val), date.today())
                if resolved:
                    r[fname] = resolved
                    continue
                parsed = _parse_known_date(str(val), [str(x) for x in date_formats])
                if parsed:
                    r[fname] = parsed
                    continue
                # If unparseable, keep original; validator will flag it.

            if ftype in ("float", "currency", "percent", "int", "integer"):
                num = _coerce_number(val)
                if num is not None:
                    r[fname] = int(num) if ftype in ("int", "integer") else float(num)

        # Normalize child row numeric/date types for common patterns
        for tname in table_fields.keys():
            items = r.get(tname)
            if not isinstance(items, list):
                continue
            new_items = []
            for it in items:
                if not isinstance(it, dict):
                    continue
                it2 = dict(it)
                for k, v in list(it2.items()):
                    lk = str(k).lower()
                    if v in (None, ""):
                        continue
                    if "date" in lk:
                        resolved = _resolve_relative_dates(str(v), date.today())
                        if resolved:
                            it2[k] = resolved
                        else:
                            parsed = _parse_known_date(str(v), [str(x) for x in date_formats])
                            if parsed:
                                it2[k] = parsed
                    if any(tok in lk for tok in ("qty", "quantity", "rate", "amount", "price")):
                        num = _coerce_number(v)
                        if num is not None:
                            it2[k] = float(num)
                new_items.append(it2)
            r[tname] = new_items

        # Doctype-level naming_series (KB root key, not in field_mappings)
        naming_series = dt_cfg.get("naming_series")
        if isinstance(naming_series, str) and naming_series.strip():
            if r.get("naming_series") in (None, ""):
                r["naming_series"] = naming_series.strip()

        # Inject defaults for missing mandatory fields
        mandatory_fields = set(dt_cfg.get("mandatory_fields") or [])
        for _, cfg in fmap.items():
            fname = cfg.get("fieldname")
            if not fname or "[]" in str(fname):
                continue
            is_mandatory = bool(cfg.get("mandatory")) or (fname in mandatory_fields)
            if not is_mandatory:
                continue
            if r.get(fname) not in (None, ""):
                continue

            dval = cfg.get("default_value")
            if dval == "today":
                r[fname] = _today()
                continue

            # If KB provided a static default
            if isinstance(dval, (str, int, float, bool)) and dval not in ("today", None):
                # Avoid copying formula-like strings here; handle only simple constants.
                if isinstance(dval, str) and any(tok in dval for tok in ("+", "fetch_from", "user_default")):
                    pass
                else:
                    r[fname] = dval
                    continue

            # Baseline-driven safe defaults for core doctypes
            if doctype == "Item":
                if fname == "item_group":
                    r[fname] = "Consumable"
                elif fname == "stock_uom":
                    r[fname] = "Nos"
            if doctype == "Customer":
                if fname == "customer_group":
                    r[fname] = "All Customer Groups"
                elif fname == "territory":
                    r[fname] = "All Territories"
                elif fname == "customer_type":
                    r[fname] = "Company"
            if doctype == "Supplier":
                if fname == "supplier_group":
                    r[fname] = "All Supplier Groups"
                elif fname == "supplier_type":
                    r[fname] = "Company"

        # Child table minimum rows: enforce empty list presence; do not invent rows.
        # Validation will still fail if business requires rows; extraction should handle that.

        out.append(r)

    return out


def normalize_mapped_payload(doctype: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Apply KB defaults to an mapped R2 payload (`records` list). Returns a new dict."""
    if not isinstance(payload, dict):
        return payload
    records = payload.get("records")
    if not isinstance(records, list):
        return payload
    out = dict(payload)
    out["records"] = apply_defaults_and_normalize(doctype, records)
    return out

