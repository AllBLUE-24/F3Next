"""
containers/OS/validation_agent/validator.py

Pure, deterministic payload validation. No I/O, no LLM, no network.
Fully unit-testable.

Input:
  payload_bundle — PayloadBundle dict (from Payload Generator)
    {
      "steps": [
        {
          "step_number": 1,
          "action":      "create",
          "doctype":     "Sales Order",
          "payload":     {...},          ← validated here
          "endpoint":    "...",
          "http_method": "POST",
        }
      ]
    }
  context — context bundle (from Context Retrieval)
    {
      "doctype_schema": {
        "mandatory_fields": [...],
        "field_mappings":   {...},
        "child_tables":     {...},
      },
      "defaults":        {...},
      "company_profile": {...},
      ...
    }

Output: ValidationResult dict
  {
    "valid":            bool,
    "errors":           [{rule_id, field, message, severity, step}],
    "warnings":         [{rule_id, field, message, severity, step}],
    "auto_corrections": [{field, original_value, corrected_value, reason, step}],
  }

5-layer validation (KB-06 order):
  1. Schema       — mandatory fields, items table structure
  2. Field types  — date format, numeric fields
  3. Business rules (local) — date logic, payment matching, warehouse
  4. Data quality warnings   — past delivery, zero rates
  5. Runtime link warnings   — customer/item existence (informational only)
"""

from __future__ import annotations

import logging
import re
from datetime import date, datetime
from typing import Any

from containers.os.validation_agent.kb_rules import rules_kb
from containers.os.payload_generator.kb_fields import field_kb
from shared.os_field_semantics import (
    cvs_registry_key_for_link,
    field_spec_for_fieldname,
    link_target_doctype,
    should_validate_link_in_cvs,
)

logger = logging.getLogger(__name__)

# ── Doctypes with "items" child tables ─────────────────────────────────────────
_ITEMS_DOCTYPES = {
    "Sales Order", "Sales Invoice", "Delivery Note",
    "Purchase Order", "Purchase Invoice", "Purchase Receipt",
    "Stock Entry", "Quotation",
}

# ── Date fields by doctype (those that must be YYYY-MM-DD) ────────────────────
_DATE_FIELDS: dict[str, list[str]] = {
    "Sales Order":      ["transaction_date", "delivery_date", "po_date"],
    "Sales Invoice":    ["posting_date", "due_date"],
    "Purchase Order":   ["transaction_date", "schedule_date"],
    "Purchase Invoice": ["posting_date", "bill_date"],
    "Purchase Receipt": ["posting_date"],
    "Delivery Note":    ["posting_date"],
    "Payment Entry":    ["posting_date"],
    "Stock Entry":      ["posting_date"],
    "Journal Entry":    ["posting_date"],
    "Item":             [],
    "Customer":         [],
    "Supplier":         [],
}

# ── Numeric fields by doctype ──────────────────────────────────────────────────
_NUMERIC_FIELDS: dict[str, list[str]] = {
    "Sales Order":      ["grand_total"],
    "Payment Entry":    ["paid_amount", "received_amount"],
}

# ── ISO date regex ─────────────────────────────────────────────────────────────
_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _is_iso_date(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    if not _ISO_DATE_RE.match(value):
        return False
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def _today() -> str:
    return date.today().isoformat()


# ── Result builder helpers ─────────────────────────────────────────────────────

def _err(rule_id: str, field: str, message: str, step: int = 1) -> dict:
    return {
        "rule_id":  rule_id,
        "field":    field,
        "message":  message,
        "severity": "error",
        "step":     step,
    }


def _warn(rule_id: str, field: str, message: str, step: int = 1) -> dict:
    return {
        "rule_id":  rule_id,
        "field":    field,
        "message":  message,
        "severity": "warning",
        "step":     step,
    }


def _correction(field: str, original: Any, corrected: Any, reason: str, step: int = 1) -> dict:
    return {
        "field":           field,
        "original_value":  original,
        "corrected_value": corrected,
        "reason":          reason,
        "step":            step,
    }


# ══════════════════════════════════════════════════════════════════════════════
# Layer 1 — Schema validation
# ══════════════════════════════════════════════════════════════════════════════

def _validate_schema(
    step_num:  int,
    action:    str,
    doctype:   str,
    payload:   dict,
    context:   dict,
    errors:    list,
    corrections: list,
) -> None:
    """
    Check mandatory fields, items table structure.
    Auto-correct missing transaction_date / posting_date.
    Only applies to create/update actions — skip for get/search/report/delete.
    """
    if action in ("get", "search", "report", "delete"):
        return

    # ── Resolve mandatory fields ───────────────────────────────────────────
    # Primary doctype uses context schema; fallback to KB-04
    if step_num == 1:
        mandatory = context.get("doctype_schema", {}).get("mandatory_fields", [])
    else:
        mandatory = field_kb().mandatory_fields(doctype)

    for field_name in mandatory:
        value = payload.get(field_name)
        if value is None or value == "" or value == []:
            # Auto-correct missing date fields
            if field_name in ("transaction_date", "posting_date"):
                today = _today()
                payload[field_name] = today
                corrections.append(_correction(
                    field_name, None, today,
                    "Auto-filled with today's date",
                    step_num,
                ))
            else:
                errors.append(_err(
                    "mandatory_fields",
                    field_name,
                    f"Field '{field_name}' is mandatory for {doctype}",
                    step_num,
                ))

    # ── Items table check ──────────────────────────────────────────────────
    if doctype in _ITEMS_DOCTYPES and action in ("create", "update"):
        items = payload.get("items", [])
        if not items:
            errors.append(_err(
                "child_table_validation",
                "items",
                f"At least one item is required for {doctype}",
                step_num,
            ))
        else:
            for i, item in enumerate(items):
                if not item.get("item_code"):
                    errors.append(_err(
                        "mandatory_fields",
                        f"items[{i}].item_code",
                        f"item_code is mandatory in items row {i + 1}",
                        step_num,
                    ))
                qty = item.get("qty")
                if qty is not None:
                    try:
                        if float(qty) <= 0:
                            errors.append(_err(
                                "field_type_validation",
                                f"items[{i}].qty",
                                f"qty must be > 0 in items row {i + 1} (got {qty})",
                                step_num,
                            ))
                    except (TypeError, ValueError):
                        errors.append(_err(
                            "field_type_validation",
                            f"items[{i}].qty",
                            f"qty must be a number in items row {i + 1}",
                            step_num,
                        ))


# ══════════════════════════════════════════════════════════════════════════════
# Layer 2 — Field type validation
# ══════════════════════════════════════════════════════════════════════════════

def _validate_field_types(
    step_num: int,
    doctype:  str,
    payload:  dict,
    errors:   list,
    corrections: list,
) -> None:
    """Check date field formats and numeric field types."""

    # ── Date fields ────────────────────────────────────────────────────────
    for field_name in _DATE_FIELDS.get(doctype, []):
        value = payload.get(field_name)
        if value is None:
            continue
        if not _is_iso_date(value):
            errors.append(_err(
                "field_type_validation",
                field_name,
                f"'{field_name}' must be a valid date in YYYY-MM-DD format (got: {value!r})",
                step_num,
            ))

    # ── Numeric fields ─────────────────────────────────────────────────────
    for field_name in _NUMERIC_FIELDS.get(doctype, []):
        value = payload.get(field_name)
        if value is None:
            continue
        try:
            float(value)
        except (TypeError, ValueError):
            errors.append(_err(
                "field_type_validation",
                field_name,
                f"'{field_name}' must be a number (got: {value!r})",
                step_num,
            ))


# ══════════════════════════════════════════════════════════════════════════════
# Layer 3 — Business rule validation (local, no ERP calls)
# ══════════════════════════════════════════════════════════════════════════════

def _validate_business_rules(
    step_num: int,
    action:   str,
    doctype:  str,
    payload:  dict,
    errors:   list,
    warnings: list,
) -> None:
    """
    Apply KB-06 business rules that can be checked locally (no ERP API call).
    Rules requiring live ERP data (credit limit, stock availability) are skipped
    and become runtime warnings only.
    """

    # ── Delivery date must be >= transaction date ──────────────────────────
    tx_date  = payload.get("transaction_date") or payload.get("posting_date")
    del_date = payload.get("delivery_date") or payload.get("schedule_date")

    if tx_date and del_date and _is_iso_date(tx_date) and _is_iso_date(del_date):
        if del_date < tx_date:
            errors.append(_err(
                "delivery_date_validation",
                "delivery_date",
                f"Delivery date ({del_date}) cannot be before transaction date ({tx_date})",
                step_num,
            ))

    # ── Payment Entry: paid_amount == received_amount (same currency) ──────
    if doctype == "Payment Entry":
        paid     = payload.get("paid_amount")
        received = payload.get("received_amount")
        paid_cur  = payload.get("paid_from_account_currency") or payload.get("currency")
        recv_cur  = payload.get("received_into_account_currency") or payload.get("currency")

        if paid is not None and received is not None:
            # Only enforce equality for same-currency payments
            if paid_cur == recv_cur:
                try:
                    if abs(float(paid) - float(received)) > 0.01:
                        errors.append(_err(
                            "paid_received_match",
                            "paid_amount",
                            f"Paid amount ({paid}) and received amount ({received}) must match for same-currency payment",
                            step_num,
                        ))
                except (TypeError, ValueError):
                    pass

    # ── Stock Entry: from_warehouse != to_warehouse (Material Transfer) ────
    if doctype == "Stock Entry":
        entry_type = payload.get("stock_entry_type", "")
        from_wh    = payload.get("from_warehouse")
        to_wh      = payload.get("to_warehouse")

        if entry_type == "Material Transfer" and from_wh and to_wh:
            if from_wh == to_wh:
                errors.append(_err(
                    "warehouse_validation",
                    "from_warehouse",
                    f"Source and target warehouses must be different for Material Transfer (both set to '{from_wh}')",
                    step_num,
                ))

    # ── Cancel / delete always get a risk warning ──────────────────────────
    if action in ("cancel", "delete"):
        warnings.append(_warn(
            "high_risk_action",
            "action",
            f"'{action.upper()}' is irreversible. Ensure this is intended before proceeding.",
            step_num,
        ))

    # ── Credit limit / stock availability: live checks → runtime warnings ──
    if doctype in ("Sales Order", "Sales Invoice") and payload.get("customer"):
        warnings.append(_warn(
            "runtime_credit_check",
            "customer",
            f"Credit limit for '{payload['customer']}' will be verified at execution time",
            step_num,
        ))


# ══════════════════════════════════════════════════════════════════════════════
# Layer 4 — Data quality warnings
# ══════════════════════════════════════════════════════════════════════════════

def _validate_data_quality(
    step_num: int,
    doctype:  str,
    payload:  dict,
    warnings: list,
) -> None:
    """Non-blocking data quality checks."""

    today = _today()

    # ── Delivery date in the past ──────────────────────────────────────────
    del_date = payload.get("delivery_date") or payload.get("schedule_date")
    if del_date and _is_iso_date(del_date) and del_date < today:
        warnings.append(_warn(
            "past_delivery_date",
            "delivery_date",
            f"Delivery date ({del_date}) is in the past",
            step_num,
        ))

    # ── Delivery date > 180 days away ──────────────────────────────────────
    if del_date and _is_iso_date(del_date):
        try:
            delta = (datetime.strptime(del_date, "%Y-%m-%d").date() - date.today()).days
            if delta > 180:
                warnings.append(_warn(
                    "far_future_delivery",
                    "delivery_date",
                    f"Delivery date ({del_date}) is more than 180 days away ({delta} days)",
                    step_num,
                ))
        except ValueError:
            pass

    # ── Zero-rate line items ───────────────────────────────────────────────
    items = payload.get("items", [])
    for i, item in enumerate(items):
        rate = item.get("rate")
        if rate is not None:
            try:
                if float(rate) == 0.0 and doctype not in ("Stock Entry",):
                    warnings.append(_warn(
                        "zero_rate_item",
                        f"items[{i}].rate",
                        f"Item '{item.get('item_code', i)}' has rate = 0",
                        step_num,
                    ))
            except (TypeError, ValueError):
                pass


# ══════════════════════════════════════════════════════════════════════════════
# Layer 5 — Runtime link warnings (informational)
# ══════════════════════════════════════════════════════════════════════════════

def _validate_runtime_links(
    step_num: int,
    action:   str,
    doctype:  str,
    payload:  dict,
    context:  dict,
    errors:   list,
    warnings: list,
) -> None:
    """
    Existence checks for Link fields that reference master data in CVS.

    Only validates fields defined in KB-04 for this doctype. Skips name/data
    fields when creating the master record itself (action=create).
    """
    profile = context.get("company_profile", {}) if isinstance(context, dict) else {}
    registry = profile.get("entity_registry", {}) if isinstance(profile, dict) else {}

    for fieldname, value in payload.items():
        if value in (None, "", [], {}):
            continue
        if fieldname == "items" and isinstance(value, list):
            _validate_items_in_cvs(step_num, doctype, value, registry, errors, warnings)
            continue

        spec = field_spec_for_fieldname(doctype, str(fieldname))
        if not spec:
            continue

        if not should_validate_link_in_cvs(action, doctype, spec):
            continue

        link_target = link_target_doctype(spec)
        reg_key = cvs_registry_key_for_link(link_target) if link_target else None
        if not reg_key:
            warnings.append(_warn(
                "runtime_link_check",
                fieldname,
                f"'{value}' will be verified against {link_target or 'master'} at execution time",
                step_num,
            ))
            continue

        known = registry.get(reg_key) or []
        known_set = {str(x).casefold() for x in known if x} if isinstance(known, list) else set()
        if known_set and str(value).casefold() not in known_set:
            rule_id = {
                "known_customers": "unknown_customer",
                "known_suppliers": "unknown_supplier",
                "known_items": "unknown_item",
                "known_warehouses": "unknown_warehouse",
            }.get(reg_key, "unknown_link")
            label = link_target or fieldname
            errors.append(_err(
                rule_id,
                fieldname,
                f"{label} '{value}' was not found in CVS master_data. Please choose an existing {label.lower()}.",
                step_num,
            ))
        elif not known_set:
            warnings.append(_warn(
                "runtime_link_check",
                fieldname,
                f"'{value}' will be verified against {link_target or 'master'} at execution time",
                step_num,
            ))


def _validate_items_in_cvs(
    step_num: int,
    doctype: str,
    items: list,
    registry: dict,
    errors: list,
    warnings: list,
) -> None:
    item_set = {str(x).casefold() for x in (registry.get("known_items") or []) if x}
    for i, item in enumerate(items if isinstance(items, list) else []):
        code = item.get("item_code") if isinstance(item, dict) else None
        if not code:
            continue
        if item_set and str(code).casefold() not in item_set:
            errors.append(_err(
                "unknown_item",
                f"items[{i}].item_code",
                f"Item '{code}' was not found in CVS master_data. Please choose an existing item.",
                step_num,
            ))
            break
        if not item_set:
            warnings.append(_warn(
                "runtime_link_check",
                "items.item_code",
                f"Item '{code}' will be verified against Item master at execution time",
                step_num,
            ))
            break


# ══════════════════════════════════════════════════════════════════════════════
# Public entry point
# ══════════════════════════════════════════════════════════════════════════════

def validate_payload_bundle(
    payload_bundle: dict,
    context:        dict,
) -> dict:
    from shared.os_field_semantics import apply_computed_defaults_to_payload
    """
    Run all 5 validation layers over every step in the payload bundle.

    Returns a ValidationResult dict:
    {
        "valid":            bool,
        "errors":           [...],
        "warnings":         [...],
        "auto_corrections": [...],
    }
    """
    # Warm up the rules KB singleton
    rules_kb()

    errors:      list[dict] = []
    warnings:    list[dict] = []
    corrections: list[dict] = []

    steps = payload_bundle.get("steps", [])
    if not steps:
        warnings.append(_warn(
            "empty_plan",
            "steps",
            "Payload bundle has no steps — nothing to validate",
            0,
        ))

    for step in steps:
        step_num = step.get("step_number", 1)
        action   = step.get("action", "create")
        doctype  = step.get("doctype", "")
        payload  = step.get("payload", {})

        if isinstance(payload, dict) and isinstance(doctype, str) and doctype.strip():
            intent = context.get("intent") if isinstance(context.get("intent"), dict) else {}
            ent = intent.get("entities") if isinstance(intent.get("entities"), dict) else {}
            step["payload"] = apply_computed_defaults_to_payload(doctype, payload, ent, context)
            payload = step["payload"]

        if not (isinstance(doctype, str) and doctype.strip()):
            errors.append(_err(
                "missing_doctype",
                "doctype",
                f"Step {step_num} has no document type (doctype) — cannot call ERPNext.",
                step_num,
            ))
            continue

        # ── Layer 1: Schema ────────────────────────────────────────────────
        _validate_schema(step_num, action, doctype, payload, context, errors, corrections)

        # ── Layer 2: Field types ───────────────────────────────────────────
        _validate_field_types(step_num, doctype, payload, errors, corrections)

        # ── Layer 3: Business rules ────────────────────────────────────────
        _validate_business_rules(step_num, action, doctype, payload, errors, warnings)

        # ── Layer 4: Data quality ──────────────────────────────────────────
        _validate_data_quality(step_num, doctype, payload, warnings)

        # ── Layer 5: Runtime link warnings ────────────────────────────────
        _validate_runtime_links(step_num, action, doctype, payload, context, errors, warnings)

    is_valid = len(errors) == 0

    return {
        "valid":            is_valid,
        "errors":           errors,
        "warnings":         warnings,
        "auto_corrections": corrections,
    }