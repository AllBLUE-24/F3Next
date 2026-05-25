"""Flatten child-table rows into parent records for validate preview display."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

_CHILD_TABLE_KEYS = ("items", "accounts", "taxes", "payment_schedule", "operations")


def flatten_records_for_preview(records: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Merge the first child-table row onto each parent so item_code, qty, etc.
    appear as top-level preview columns instead of nested arrays.
    """
    if not records:
        return [], []

    flat_records: List[Dict[str, Any]] = []
    child_cols: List[str] = []
    child_seen: set = set()

    for rec in records:
        if not isinstance(rec, dict):
            flat_records.append(rec)
            continue

        flat: Dict[str, Any] = {}
        for key, val in rec.items():
            if key in _CHILD_TABLE_KEYS and isinstance(val, list) and val and isinstance(val[0], dict):
                for ck, cv in val[0].items():
                    if ck in rec and ck not in _CHILD_TABLE_KEYS:
                        col = f"{key}.{ck}"
                    else:
                        col = ck
                    flat[col] = cv
                    if col not in child_seen:
                        child_seen.add(col)
                        child_cols.append(col)
            else:
                flat[key] = val

        flat_records.append(flat)

    if not isinstance(records[0], dict):
        return flat_records, []

    parent_cols = [k for k in records[0].keys() if k not in _CHILD_TABLE_KEYS]
    columns = parent_cols + [c for c in child_cols if c not in parent_cols]
    if flat_records:
        for k in flat_records[0].keys():
            if k not in columns:
                columns.append(k)

    return flat_records, columns
