"""
containers/OS/payload_generator/payload_builder.py

Pure, deterministic payload construction. No I/O, no LLM.
Fully unit-testable.

FIXES vs previous version:
  - company: now read from context.company_profile.company (real name) not defaults.company
  - warehouse: NEVER injected from defaults into items — let ERPNext item master default
  - selling_price_list / buying_price_list: only injected if explicitly in company profile
  - uom: only added if user provided it; ERPNext uses item master default otherwise
"""

from __future__ import annotations

import copy
import logging
from datetime import date
from typing import Any

from containers.os.payload_generator.kb_fields import field_kb
from shared.os_field_semantics import (
    apply_field_defaults_to_payload,
    map_entities_to_payload_fields,
    normalize_entities_for_doctype,
    resolve_entity_to_field,
)

logger = logging.getLogger(__name__)

# ── Company name resolution ───────────────────────────────────────────────────

def _get_company(context: dict) -> str:
    """
    Get the real company name from the context bundle.
    Priority:
      1. context.company_profile.company         — real name from deployment_details
      2. context.company_profile.default_company — set during profile construction
      3. context.company_profile.company_name    — from projects table
      4. context.defaults.company                — last resort (may be dummy)
    """
    profile = context.get("company_profile", {})
    company = (
        profile.get("company")           or
        profile.get("default_company")   or
        profile.get("company_name")      or
        context.get("defaults", {}).get("company", "")
    )
    return company


# ── Default value injection ───────────────────────────────────────────────────

def _inject_defaults(payload: dict, doctype: str, context: dict, kb) -> dict:
    """
    Fill mandatory fields that weren't in the user's intent.
    Uses REAL company name from context.company_profile.
    Does NOT inject warehouse or price_list — ERPNext uses its own defaults for those.
    """
    today = date.today().isoformat()

    # Company — always required, always from real profile
    if "company" not in payload:
        payload["company"] = _get_company(context)

    # Date fields
    if doctype in ("Sales Order", "Purchase Order"):
        if "transaction_date" not in payload:
            payload["transaction_date"] = today
        if "delivery_date" not in payload and doctype == "Sales Order":
            payload["delivery_date"] = kb.today_plus_days(10)
        if "schedule_date" not in payload and doctype == "Purchase Order":
            payload["schedule_date"] = kb.today_plus_days(7)

    if doctype in ("Sales Invoice", "Payment Entry", "Stock Entry",
                   "Delivery Note", "Purchase Invoice", "Purchase Receipt"):
        if "posting_date" not in payload:
            payload["posting_date"] = today

    # NOTE: We deliberately do NOT inject:
    #   - warehouse        → ERPNext fetches from item master / company default
    #   - selling_price_list → ERPNext fetches from customer / company settings
    #   - buying_price_list  → same
    #   - currency         → ERPNext fetches from customer / company
    # These fields are safe to omit — ERPNext fills them from its own settings.
    # Injecting them risks sending a value that doesn't exist in the real instance.

    return payload


# ── Items / child table builder ───────────────────────────────────────────────

def _build_items(items_entities: list, doctype: str, context: dict, kb) -> list[dict]:
    """
    Convert items list into ERPNext child table rows.
    Only includes fields the user explicitly provided.
    Warehouse is NEVER injected from defaults — let ERPNext use item master default.
    """
    result: list[dict] = []

    for item in items_entities:
        row: dict[str, Any] = {}

        if item.get("item_code"):
            row["item_code"] = item["item_code"]

        if item.get("qty") is not None:
            row["qty"] = float(item["qty"])

        if item.get("rate") is not None:
            row["rate"] = kb.resolve_amount(item["rate"])

        # UOM: only include if user specified it — ERPNext uses item master stock_uom otherwise
        uom = item.get("uom", "")
        if uom and uom.lower() not in ("units", "unit", "nos", ""):
            row["uom"] = kb.resolve_uom(uom)
        # Do NOT default to "Nos" — "Nos" may not be the correct UOM in the real instance

        # Warehouse: ONLY from user's explicit input — NEVER from defaults
        wh = item.get("warehouse", "")
        if wh:
            row["warehouse"] = wh
        # else: omit — ERPNext fills from item master or company default warehouse

        if item.get("description"):
            row["description"] = item["description"]

        result.append(row)

    return result


# ── Per-action payload builders ───────────────────────────────────────────────

def _build_create_payload(step: dict, entities: dict, context: dict, kb) -> dict:
    """Build full document payload for a 'create' step."""
    doctype = step.get("doctype", "")
    entities = normalize_entities_for_doctype(doctype, entities)
    payload: dict[str, Any] = map_entities_to_payload_fields(doctype, entities)

    items_list = entities.get("items", [])
    if items_list:
        payload["items"] = _build_items(items_list, doctype, context, kb)

    for date_key in ("transaction_date", "posting_date", "delivery_date",
                     "schedule_date", "due_date"):
        if entities.get(date_key):
            resolved = resolve_entity_to_field(doctype, date_key)
            fn = (
                str(resolved[1].get("fieldname"))
                if resolved
                else kb.fieldname(doctype, date_key)
            )
            payload[fn] = kb.resolve_date(entities[date_key])

    for ref_key in ("po_no", "so_no", "dn_no", "invoice_no", "reference_no",
                    "payment_reference", "lr_no"):
        if entities.get(ref_key):
            resolved = resolve_entity_to_field(doctype, ref_key)
            fn = (
                str(resolved[1].get("fieldname"))
                if resolved
                else kb.fieldname(doctype, ref_key)
            )
            payload[fn] = entities[ref_key]

    if doctype == "Payment Entry":
        if entities.get("payment_type"):
            payload["payment_type"] = entities["payment_type"]
        if entities.get("party_type"):
            payload["party_type"] = entities["party_type"]
            payload["party"] = entities.get("customer") or entities.get("supplier", "")
        if entities.get("amount"):
            amount = kb.resolve_amount(entities["amount"])
            payload["paid_amount"] = amount
            payload["received_amount"] = amount
        if entities.get("mode_of_payment"):
            payload["mode_of_payment"] = entities["mode_of_payment"]

    if doctype == "Stock Entry":
        if entities.get("stock_entry_type"):
            payload["stock_entry_type"] = entities["stock_entry_type"]
        if entities.get("from_warehouse"):
            payload["from_warehouse"] = entities["from_warehouse"]
        if entities.get("to_warehouse"):
            payload["to_warehouse"] = entities["to_warehouse"]
        if entities.get("project"):
            payload["project"] = entities["project"]

    if doctype == "Item":
        if entities.get("item_name") and "item_name" not in payload:
            payload["item_name"] = entities["item_name"]
        if entities.get("is_stock_item") is not None:
            payload["is_stock_item"] = int(bool(entities["is_stock_item"]))
        if entities.get("uom"):
            payload["stock_uom"] = kb.resolve_uom(entities["uom"])

    if doctype == "Customer" and entities.get("gstin"):
        payload["gstin"] = entities["gstin"]
        payload["gst_category"] = "Registered Regular"

    payload = apply_field_defaults_to_payload(doctype, payload)
    payload = _inject_defaults(payload, doctype, context, kb)

    return payload


def _build_submit_payload(step: dict) -> dict:
    source_step = step.get("source_step")
    docname_ref = f"__step_{source_step}_result__" if source_step else "__prev_result__"
    return {"docname": docname_ref, "docstatus": 1}


def _build_cancel_payload(step: dict) -> dict:
    source_step = step.get("source_step")
    docname_ref = f"__step_{source_step}_result__" if source_step else "__prev_result__"
    return {"docname": docname_ref, "docstatus": 2}


def _build_create_from_payload(step: dict, entities: dict, context: dict, kb) -> dict:
    source_step  = step.get("source_step")
    source_ref   = f"__step_{source_step}_result__" if source_step else "__prev_result__"
    doctype      = step.get("doctype", "")
    source_dtype = step.get("source_doctype", "")
    fetch_fields = step.get("fetch_fields", [])

    overrides: dict = {}
    today = date.today().isoformat()
    if doctype in ("Sales Invoice", "Purchase Invoice"):
        overrides["posting_date"] = today
    if doctype == "Delivery Note":
        overrides["posting_date"] = today

    return {
        "__create_from__": True,
        "source_doctype":  source_dtype,
        "source_name":     source_ref,
        "fetch_fields":    fetch_fields,
        "overrides":       overrides,
    }


def _build_get_payload(step: dict, entities: dict) -> dict:
    docname = (
        entities.get("so_no") or entities.get("dn_no") or entities.get("invoice_no") or
        entities.get("document_name") or entities.get("name") or ""
    )
    if not docname and step.get("source_step"):
        docname = f"__step_{step['source_step']}_result__"
    return {"docname": docname}


def _build_search_payload(entities: dict) -> dict:
    filters: list = []
    if entities.get("customer"):
        filters.append(["customer", "=", entities["customer"]])
    if entities.get("supplier"):
        filters.append(["supplier", "=", entities["supplier"]])
    limit = entities.get("limit", 20)
    return {"filters": filters, "limit": limit, "fields": ["name", "status"]}


def _build_report_payload(intent_dict: dict, entities: dict, context: dict) -> dict:
    report_map = {
        "report_stock_balance":       "Stock Balance",
        "report_accounts_receivable": "Accounts Receivable",
        "report_accounts_payable":    "Accounts Payable",
    }
    intent_id   = intent_dict.get("intent_id", "")
    report_name = report_map.get(intent_id, "Stock Balance")
    return {
        "report_name": report_name,
        "filters": {
            "company":   _get_company(context),
            "from_date": entities.get("from_date", ""),
            "to_date":   entities.get("to_date", ""),
        },
    }


# ── Main entry point ──────────────────────────────────────────────────────────

def build_payload_bundle(plan: dict, context: dict, intent_dict: dict) -> dict:
    """
    Build the full PayloadBundle for all steps in the plan.
    Pure function — no I/O.
    """
    kb       = field_kb()
    entities = intent_dict.get("entities", {})
    steps    = plan.get("steps", [])

    if not steps:
        logger.warning("build_payload_bundle: plan has no steps")
        return {"steps": []}

    # Log what company name we're using
    company = _get_company(context)
    is_dummy = context.get("company_profile", {}).get("is_dummy", False)
    logger.info(
        "Payload bundle: %d step(s) for intent=%s doctype=%s  company=%s%s",
        len(steps),
        intent_dict.get("intent_id", "?"),
        intent_dict.get("target_doctype", "?"),
        company,
        " (dummy)" if is_dummy else "",
    )

    built_steps: list[dict] = []

    for step in steps:
        step_num = step.get("step_number", len(built_steps) + 1)
        action   = step.get("action", "create")
        doctype  = step.get("doctype", "")

        step_entities = {**entities, **step.get("entities", {})}

        source_step = step.get("source_step")
        step_ref    = f"__step_{source_step}_result__" if source_step else ""

        if step.get("payload_template"):
            payload = copy.deepcopy(step.get("payload_template", {}))
            notes = step.get("description") or f"Prebuilt payload for {doctype}"

        elif action == "create":
            payload = _build_create_payload(step, step_entities, context, kb)
            notes   = f"Create new {doctype}"

        elif action == "create_from":
            payload = _build_create_from_payload(step, step_entities, context, kb)
            notes   = f"Create {doctype} from {step.get('source_doctype', '?')} (step {source_step})"

        elif action == "submit":
            payload = _build_submit_payload(step)
            notes   = f"Submit {doctype} created in step {source_step}"

        elif action == "cancel":
            payload = _build_cancel_payload(step)
            notes   = f"Cancel {doctype} from step {source_step}"

        elif action in ("get", "get_document"):
            payload = _build_get_payload(step, step_entities)
            notes   = f"Fetch {doctype}"

        elif action == "search":
            payload = _build_search_payload(step_entities)
            notes   = f"Search {doctype}"

        elif action == "report":
            payload = _build_report_payload(intent_dict, step_entities, context)
            notes   = f"Run report for {doctype}"

        elif action == "update":
            payload = _build_create_payload(step, step_entities, context, kb)
            if step_ref:
                payload["docname"] = step_ref
            notes = f"Update {doctype}"

        elif action == "validate_data":
            payload = {"data": step_entities}
            notes   = "Local validation step — no API call"

        elif action in ("bulk_create", "notify_completion"):
            payload = {"items": step_entities.get("items", [])}
            notes   = f"Bulk {action} {doctype}"

        else:
            logger.warning("Unknown action '%s' for step %d — using empty payload", action, step_num)
            payload = {}
            notes   = f"Unknown action: {action}"

        built_steps.append({
            "step_number": step_num,
            "action":      action,
            "doctype":     doctype,
            "payload":     payload,
            "notes":       notes,
        })

        logger.info(
            "  step %d [%s]: %s %s  (%d payload keys)",
            step_num,
            step.get("step_role", "main"),
            action,
            doctype,
            len(payload),
        )

    return {"steps": built_steps}