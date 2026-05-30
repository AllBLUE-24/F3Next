"""
Workflow-safe gate helpers (no KB/pathlib imports).

Temporal sandbox blocks transitive imports from shared.erp_semantics / containers.knowledge_base.
Keep this module limited to static sets and plain dict inspection.
"""

from __future__ import annotations

from typing import Any

# Mirrors containers/knowledge_base/erpnext/schema/shared/os_validation.json erp_autofill_fields
ERP_AUTOFILL_FIELDS: frozenset[str] = frozenset({
    "naming_series",
    "company",
    "currency",
    "conversion_rate",
    "selling_price_list",
    "buying_price_list",
    "price_list_currency",
    "plc_conversion_rate",
    "order_type",
    "transaction_date",
    "posting_date",
    "status",
    "title",
})

FIXABLE_VALIDATION_RULE_IDS: frozenset[str] = frozenset({
    "mandatory_fields",
    "child_table_validation",
    "unknown_customer",
    "unknown_supplier",
    "unknown_item",
    "unknown_warehouse",
})


def is_autofill_field(fieldname: str) -> bool:
    return str(fieldname or "") in ERP_AUTOFILL_FIELDS


def is_fixable_validation(validation: dict) -> bool:
    """True when validation errors can be resolved via clarification (non-autofill)."""
    errs = validation.get("errors", []) if isinstance(validation, dict) else []
    for e in errs if isinstance(errs, list) else []:
        if not isinstance(e, dict):
            continue
        if e.get("rule_id") not in FIXABLE_VALIDATION_RULE_IDS:
            continue
        if e.get("rule_id") == "mandatory_fields" and is_autofill_field(str(e.get("field") or "")):
            continue
        return True
    return False
