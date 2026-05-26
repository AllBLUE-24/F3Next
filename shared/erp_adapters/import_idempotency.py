"""
Business-key idempotency for ERPNext import (create_record).

Prevents duplicate BOM / Work Order / master rows when re-importing the same
mapped corpus onto a site that already has matching documents.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

# Doctype-specific idempotency: filter fields on the ERPNext document.
# ``prefer_submitted`` picks docstatus=1 over draft when multiple matches exist.
_IMPORT_RULES: Dict[str, Dict[str, Any]] = {
    "BOM": {
        "fields": ["item"],
        "optional_fields": ["company"],
        "prefer_submitted": True,
        "prefer_default": True,
    },
    "Work Order": {
        "fields": ["production_item", "bom_no"],
        "optional_fields": ["company"],
        "fallback_fields": ["production_item"],
        "prefer_submitted": False,
    },
    "Item": {"fields": ["item_code"]},
    "Supplier": {"fields": ["supplier_name"]},
    "Customer": {"fields": ["customer_name"]},
    "Project": {"fields": ["project_name"], "optional_fields": ["company"]},
}


def _merge_policies_dedupe() -> Dict[str, str]:
    try:
        from containers.knowledge_base.erpnext.schema.compose import merge_policies

        return dict((merge_policies().get("dedupe_key") or {}))
    except Exception:
        return {}


def build_idempotency_filters(
    doctype: str,
    data: dict[str, Any],
    *,
    use_fallback: bool = False,
) -> Optional[List[List[Any]]]:
    """Build ERPNext list_records filters from mapped row data."""
    rule = _IMPORT_RULES.get(doctype)
    if not rule:
        dedupe_key = _merge_policies_dedupe().get(doctype)
        if dedupe_key and data.get(dedupe_key) not in (None, ""):
            return [[dedupe_key, "=", data[dedupe_key]]]
        return None

    field_names: Sequence[str]
    if use_fallback and rule.get("fallback_fields"):
        field_names = rule["fallback_fields"]
    else:
        field_names = rule["fields"]

    filters: List[List[Any]] = []
    for fname in field_names:
        val = data.get(fname)
        if val in (None, ""):
            return None
        filters.append([fname, "=", val])

    for fname in rule.get("optional_fields") or []:
        val = data.get(fname)
        if val not in (None, ""):
            filters.append([fname, "=", val])

    return filters or None


def pick_best_existing(
    records: List[dict[str, Any]],
    *,
    prefer_submitted: bool = False,
    prefer_default: bool = False,
) -> Optional[dict[str, Any]]:
    """Choose the best matching row when multiple ERPNext docs match."""
    if not records:
        return None
    if len(records) == 1:
        return records[0]

    def sort_key(rec: dict[str, Any]) -> Tuple[int, int, str]:
        docstatus = int(rec.get("docstatus") or 0)
        is_default = 1 if rec.get("is_default") in (1, True, "1") else 0
        submitted_rank = docstatus if prefer_submitted else 0
        default_rank = is_default if prefer_default else 0
        return (submitted_rank, default_rank, str(rec.get("name") or ""))

    return sorted(records, key=sort_key, reverse=True)[0]


async def find_existing_record(
    adapter: Any,
    doctype: str,
    data: dict[str, Any],
) -> Optional[dict[str, Any]]:
    """
    Return an existing ERPNext document matching business keys, or None.

    Tries primary key fields first, then optional fallback (e.g. WO by production_item only).
    """
    rule = _IMPORT_RULES.get(doctype) or {}
    list_fields = ["name", "docstatus"]
    if rule.get("prefer_default"):
        list_fields.append("is_default")
    for fname in rule.get("fields") or []:
        if fname not in list_fields:
            list_fields.append(fname)

    for use_fallback in (False, True):
        filters = build_idempotency_filters(doctype, data, use_fallback=use_fallback)
        if not filters:
            continue
        try:
            rows = await adapter.list_records(
                doctype,
                list_fields,
                filters=filters,
                limit=10,
            )
        except Exception:
            continue
        if not rows:
            continue
        return pick_best_existing(
            rows,
            prefer_submitted=bool(rule.get("prefer_submitted")),
            prefer_default=bool(rule.get("prefer_default")),
        )
    return None
