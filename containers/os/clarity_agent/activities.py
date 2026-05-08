"""
containers/OS/clarity_agent/activities.py

Temporal activities for the Clarity Agent.
Registered on: os-main-queue

SDK:
  - _call_llm / resolve_ambiguity : langchain_google_genai via llm_router
  - _call_agentic_llm (tool loop) : google-genai (google.genai) — new official SDK
    Replaces deprecated google-generativeai which caused malformed JSON responses.

Key improvements:
  - JSON enforcement: response_mime_type='application/json' prevents markdown fences
  - Tool schema: explicit FunctionDeclaration (no stub Python function introspection)
  - Tool response: typed FunctionResponse Part (not raw dict)
  - Agentic loop: contents-list based (not stateful chat session)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from datetime import date, timedelta
from typing import Any, List, Optional

from dotenv import load_dotenv
load_dotenv()

from pydantic import BaseModel, Field
from temporalio import activity

logger = logging.getLogger(__name__)

from shared.os_metrics import OS_CLARITY_AMBIGUITY_TOTAL, OS_CLARITY_FALLBACK_TOTAL

# ── Intent Pydantic schema (used for response_schema in Phase 2) ──────────────

class _Ambiguity(BaseModel):
    field: str
    question: str
    required: bool = True

class _Item(BaseModel):
    # NO defaults — every field in required[] forces LLM to generate them explicitly
    item_code: str
    qty: float
    uom: Optional[str]
    rate: Optional[float]
    warehouse: Optional[str]

class _Entities(BaseModel):
    # Keep these as common fields, but allow arbitrary extra entity fields
    # so Clarity can handle any doctype without schema edits.
    customer:         Optional[str] = None
    supplier:         Optional[str] = None
    items:            List[_Item] = Field(default_factory=list)
    transaction_date: Optional[str]
    delivery_date:    Optional[str]
    due_date:         Optional[str]
    posting_date:     Optional[str]
    amount:           Optional[float]
    currency:         Optional[str]
    payment_type:     Optional[str]
    mode_of_payment:  Optional[str]
    from_warehouse:   Optional[str]
    to_warehouse:     Optional[str]
    stock_entry_type: Optional[str]
    extra:            dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "allow"}

class _IntentSchema(BaseModel):
    intent_id:             str
    action:                str
    target_doctype:        str
    confidence:            float
    risk_level:            str
    requires_confirmation: bool
    has_ambiguities:       bool
    ambiguities:           List[_Ambiguity] = Field(default_factory=list)
    entities:              _Entities

# ── Model config ──────────────────────────────────────────────────────────────
_MAX_TOKENS = 1200

# ── LLM call with retry on quota ──────────────────────────────────────────────

async def _call_llm(prompt: str, max_retries: int = 3) -> dict:
    """
    Call Gemini and parse the JSON response.
    Attempts JSON repair if response is truncated.
    """
    from langchain_core.messages import HumanMessage
    from llm_router import invoke_smart_llm

    try:
        response = await invoke_smart_llm([HumanMessage(content=prompt)], temperature=0.1, max_output_tokens=_MAX_TOKENS)
        raw = response.content.strip()

        # Strip markdown fences
        cleaned = re.sub(r'^```(?:json)?\s*', '', raw, flags=re.MULTILINE)
        cleaned = re.sub(r'\s*```\s*$', '', cleaned, flags=re.MULTILINE).strip()

        # Attempt parse
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            # Pass 1: sanitize common Gemini malformations
            sanitized = _sanitize_json(cleaned)
            try:
                return json.loads(sanitized)
            except json.JSONDecodeError:
                pass
            # Pass 2: repair truncated JSON
            repaired = _repair_json(sanitized)
            if repaired:
                return json.loads(repaired)
            raise

    except Exception as e:
        raise ValueError(f"LLM call failed: {e}")




# ── Prompt builder ────────────────────────────────────────────────────────────

def _resolve_relative_dates(prompt: str, today: date) -> str:
    """
    Pre-resolve relative date expressions in the prompt before sending to LLM.
    Replaces: 'next Friday', 'tomorrow', 'next week', '+7 days', etc.
    with absolute ISO dates so the model never needs to do date arithmetic.
    """
    import re as _re

    weekdays = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
                "friday": 4, "saturday": 5, "sunday": 6}

    result = prompt

    # "next <weekday>" → ISO date
    def next_weekday(target_wd: int) -> str:
        days = (target_wd - today.weekday()) % 7
        if days == 0:
            days = 7   # "next Friday" when today IS Friday means 7 days away
        return (today + timedelta(days=days)).isoformat()

    for name, wd in weekdays.items():
        pattern = _re.compile(rf'\bnext\s+{name}\b', _re.IGNORECASE)
        result   = pattern.sub(next_weekday(wd), result)
        # also handle "this <weekday>" = same week, or next occurrence
        pattern2 = _re.compile(rf'\bthis\s+{name}\b', _re.IGNORECASE)
        days     = (wd - today.weekday()) % 7
        abs_date = (today + timedelta(days=days)).isoformat()
        result   = pattern2.sub(abs_date, result)

    # "tomorrow"
    result = _re.sub(r'\btomorrow\b', (today + timedelta(days=1)).isoformat(), result, flags=_re.IGNORECASE)

    # "next week"
    result = _re.sub(r'\bnext\s+week\b', (today + timedelta(days=7)).isoformat(), result, flags=_re.IGNORECASE)

    # "in N days"
    def replace_in_n_days(m):
        n = int(m.group(1))
        return (today + timedelta(days=n)).isoformat()
    result = _re.sub(r'\bin\s+(\d+)\s+days?\b', replace_in_n_days, result, flags=_re.IGNORECASE)

    return result


def _build_extract_prompt(prompt: str, erp_type: str, session_context: list,
                           clarifications: list) -> str:
    today_date = date.today()
    today      = today_date.isoformat()

    # Pre-resolve relative dates BEFORE sending to model
    resolved_prompt = _resolve_relative_dates(prompt, today_date)

    session_str = ""
    if session_context:
        last       = session_context[-3:]
        session_str = "\nRecent session:\n" + "\n".join(
            f"  User: {c.get('prompt','')}\n  System: {c.get('response','')}"
            for c in last
        )

    clarif_str = ""
    if clarifications:
        clarif_str = "\nClarifications already provided:\n" + "\n".join(
            f"  Q: {c.get('question','')}  A: {c.get('answer','')}"
            for c in clarifications
        )

    try:
        from containers.os.clarity_agent.kb_loader import kb as _kb
        _intent_ids = ", ".join(_kb().intent_ids())
    except Exception:
        _intent_ids = (
            "create_sales_order, create_purchase_order, create_sales_invoice, "
            "create_purchase_invoice, create_delivery_note, create_payment_entry, "
            "create_stock_entry, create_journal_entry, submit_document, cancel_document, "
            "get_document, search_documents, generate_report, create_customer, create_supplier, "
            "create_item, create_quotation"
        )

    return f"""You are an ERP command parser for {erp_type.upper()}. Today is {today}.

Your job: extract structured data from ERP commands and return ONLY a JSON object.

---
EXAMPLE INPUT:
"Create SO for Sunrise Pharma — 200 units of PARA-500 at ₹12 each, deliver by 2026-04-01"

EXAMPLE OUTPUT:
{{
  "intent_id": "create_sales_order",
  "category": "create",
  "target_doctype": "Sales Order",
  "action": "create",
  "erp_type": "erpnext",
  "entities": {{
    "customer": "Sunrise Pharma",
    "supplier": null,
    "items": [{{"item_code": "PARA-500", "qty": 200, "rate": 12, "warehouse": null, "uom": null}}],
    "transaction_date": "{today}",
    "delivery_date": "2026-04-01",
    "amount": null,
    "currency": null,
    "payment_type": null,
    "mode_of_payment": null,
    "from_warehouse": null,
    "to_warehouse": null,
    "stock_entry_type": null,
    "company": null,
    "extra": {{}}
  }},
  "confidence": 0.95,
  "ambiguities": [],
  "has_ambiguities": false,
  "risk_level": "low",
  "requires_confirmation": false,
  "raw_prompt": "Create SO for Sunrise Pharma — 200 units of PARA-500 at ₹12 each, deliver by 2026-04-01"
}}
---

INTENT IDs:
  {_intent_ids}

MASTER DATA RULES:
  "Create a customer named X"  → create_customer, target_doctype=Customer, entities.customer=X
  "Add supplier X"             → create_supplier, target_doctype=Supplier, entities.supplier=X
  "Create item X"              → create_item,     target_doctype=Item

RISK LEVELS:
  low=create draft   medium=update existing   high=submit/cancel/delete   critical=bulk

CRITICAL RULES:
  1. Extract EXACTLY what the user says — customer name, item codes, quantities, rates
  2. dates must be absolute ISO format YYYY-MM-DD (all relative dates already resolved)
  3. If multiple items mentioned, put ALL of them in the items array
  4. ambiguities=[] always unless the command is genuinely ambiguous (e.g. two customers named "ABC")
  5. NEVER put null for customer or items if they are clearly stated in the command
  6. Return ONLY the JSON — no explanation, no markdown, no ```json fences{session_str}{clarif_str}

---
NOW PARSE THIS COMMAND:
"{resolved_prompt}"

Return ONLY the JSON object:"""


def _fallback_intent(prompt: str, erp_type: str, reason: str) -> dict:
    """
    Deterministic fallback when LLM fails.
    Uses keyword matching to guess intent + party type.

    FIX: now correctly sets supplier vs customer based on intent,
         handles master data intents (create_customer, create_supplier, create_item),
         and uses a stop-word-aware party extractor.
    """
    p = prompt.lower()
    today = date.today().isoformat()

    # ── Intent detection (order matters — most specific first) ───────────────
    # Master data: use regex to handle "create a customer", "add new customer", etc.
    # Use tight match: verb must be followed DIRECTLY by (optional article +) noun
    # This avoids "Create SO for ABC ... Product-001" matching create_item
    if re.search(r'\b(create|add|new)\s+(?:an?\s+|the\s+|new\s+)?customer\b', p):
        intent_id, doctype, action, category = 'create_customer', 'Customer', 'create', 'create'
    elif re.search(r'\b(create|add|new)\s+(?:an?\s+|the\s+|new\s+)?supplier\b', p):
        intent_id, doctype, action, category = 'create_supplier', 'Supplier', 'create', 'create'
    elif re.search(r'\b(create|add|new)\s+(?:an?\s+|the\s+|new\s+)?(?:item|product)\b', p):
        intent_id, doctype, action, category = 'create_item', 'Item', 'create', 'create'
    # Transactional docs — specific compound phrases BEFORE generic single words
    elif any(k in p for k in ['purchase invoice', 'pinv']):
        intent_id, doctype, action, category = 'create_purchase_invoice', 'Purchase Invoice', 'create', 'create'
    elif any(k in p for k in ['sales invoice', 'sinv']):
        intent_id, doctype, action, category = 'create_sales_invoice', 'Sales Invoice', 'create', 'create'
    elif any(k in p for k in ['purchase order', ' po ', 'po for']):
        intent_id, doctype, action, category = 'create_purchase_order', 'Purchase Order', 'create', 'create'
    elif any(k in p for k in ['sales order', ' so ', 'so for']):
        intent_id, doctype, action, category = 'create_sales_order', 'Sales Order', 'create', 'create'
    elif any(k in p for k in ['invoice', 'bill from', 'sinv']):
        intent_id, doctype, action, category = 'create_sales_invoice', 'Sales Invoice', 'create', 'create'
    elif any(k in p for k in ['purchase', 'buying', 'procure', 'buy ']):
        intent_id, doctype, action, category = 'create_purchase_order', 'Purchase Order', 'create', 'create'
    elif any(k in p for k in ['sell', 'customer order', 'bill']):
        intent_id, doctype, action, category = 'create_sales_order', 'Sales Order', 'create', 'create'
    elif any(k in p for k in ['payment', 'pay', 'receipt']):
        intent_id, doctype, action, category = 'create_payment_entry', 'Payment Entry', 'create', 'create'
    elif any(k in p for k in ['stock entry', 'transfer', 'material']):
        intent_id, doctype, action, category = 'create_stock_entry', 'Stock Entry', 'create', 'create'
    elif any(k in p for k in ['delivery', 'dispatch', 'ship']):
        intent_id, doctype, action, category = 'create_delivery_note', 'Delivery Note', 'create', 'create'
    elif any(k in p for k in ['quotation', 'quote']):
        intent_id, doctype, action, category = 'create_quotation', 'Quotation', 'create', 'create'
    elif any(k in p for k in ['submit', 'confirm']):
        intent_id, doctype, action, category = 'submit_document', 'Sales Order', 'submit', 'workflow'
    elif any(k in p for k in ['cancel']):
        intent_id, doctype, action, category = 'cancel_document', 'Sales Order', 'cancel', 'workflow'
    elif any(k in p for k in ['report', 'show', 'list', 'get', 'find', 'search']):
        intent_id, doctype, action, category = 'search_documents', 'Sales Order', 'search', 'read'
    else:
        intent_id, doctype, action, category = 'create_sales_order', 'Sales Order', 'create', 'create'

    # ── Party extraction ──────────────────────────────────────────────────────
    # Stop words: action verbs and quantity words that should NOT be part of a name
    _PARTY_STOP = r'(?:\s+(?:buying|selling|for|to|from|named|called|with|having|at|@|₹)\b|\s*[—\-–,]|\s*\d|\s*$)'

    # For purchase orders and supplier-based intents → extract supplier
    _is_supplier_intent = intent_id in (
        'create_purchase_order', 'create_purchase_invoice', 'create_supplier'
    )

    customer = None
    supplier = None
    party_name = None

    # "named X" or "called X" → master data name
    m_named = re.search(r'(?:named|called)\s+([A-Za-z0-9 &\.\-]+?)(?:' + _PARTY_STOP + r')', prompt, re.IGNORECASE)
    if m_named:
        party_name = m_named.group(1).strip()

    # "customer , X" → master data name
    if not party_name and intent_id in ('create_customer', 'create_supplier'):
        m_comma = re.search(r'(?:customer|supplier)\s*,\s*([A-Za-z0-9 &\.\-]+?)(?:' + _PARTY_STOP + r')', prompt, re.IGNORECASE)
        if m_comma:
            party_name = m_comma.group(1).strip()

    # "for X" or "from X" → party in transactional docs
    # Skip role words like "customer"/"supplier"/"the" before the actual name
    if not party_name:
        m_party = re.search(
            r'(?:for|from)\s+(?:customer\s+|supplier\s+|the\s+|a\s+)?([A-Za-z0-9 &\.\-]+?)(?:' + _PARTY_STOP + r')',
            prompt, re.IGNORECASE
        )
        if m_party:
            party_name = m_party.group(1).strip()

    if party_name:
        if _is_supplier_intent:
            supplier = party_name
        elif intent_id == 'create_customer':
            customer = party_name   # "create customer named Stark" → customer field
        else:
            customer = party_name

    # ── Item extraction ───────────────────────────────────────────────────────
    # Common unit-of-measurement words that should NEVER be treated as item codes
    _UOM_STOP = {"kg", "kgs", "ltr", "ltrs", "litre", "litres", "liter", "liters",
                 "pcs", "nos", "nos.", "units", "unit", "box", "boxes", "bag", "bags",
                 "dozen", "pair", "pairs", "set", "sets", "roll", "rolls", "mtr", "mtrs",
                 "gms", "gm", "gram", "grams", "ton", "tons", "tonne", "ml", "ft", "inch"}

    items = []
    m_item = re.search(
        r'(\d+(?:\.\d+)?)\s+(?:units?|pcs?|nos?|qty)?\s*(?:of\s+)?([A-Z0-9][A-Z0-9\-\.]+)',
        prompt, re.IGNORECASE
    )
    m_rate = re.search(r'(?:@|at|₹|rs\.?|inr)\s*(\d+(?:\.\d+)?)', prompt, re.IGNORECASE)
    if m_item:
        candidate_code = m_item.group(2)
        if candidate_code.lower() not in _UOM_STOP:  # ← never capture 'kgs', 'ltr', etc.
            items = [{
                "item_code": candidate_code,
                "qty":       float(m_item.group(1)),
                "rate":      float(m_rate.group(1)) if m_rate else None,
                "warehouse": None,
                "uom":       None,
            }]

    logger.warning(
        "extract_intent: using keyword fallback (LLM failed: %s). "
        "Guessed intent=%s doctype=%s customer=%s items=%d",
        reason[:80], intent_id, doctype, customer or supplier, len(items),
    )

    ambiguities: list[dict] = []

    def _req(field: str, question: str) -> None:
        ambiguities.append({"field": field, "question": question, "required": True})

    # Minimal safety: if required information is missing, force clarification.
    if doctype in ("Sales Order", "Sales Invoice", "Delivery Note", "Quotation"):
        if not customer:
            _req("customer", f"Which customer is this {doctype} for?")
        if not items:
            _req("items", f"What item(s) should be included in this {doctype}, and what quantity for each?")
    if doctype in ("Purchase Order", "Purchase Invoice", "Purchase Receipt"):
        if not supplier:
            _req("supplier", f"Which supplier is this {doctype} for?")
        if not items:
            _req("items", f"What item(s) should be included in this {doctype}, and what quantity for each?")

    return {
        "intent_id":              intent_id,
        "category":               category,
        "target_doctype":         doctype,
        "action":                 action,
        "erp_type":               erp_type,
        "entities": {
            "customer":           customer,
            "supplier":           supplier,
            "items":              items,
            "transaction_date":   today,
            "delivery_date":      None,
            "due_date":           None,
            "posting_date":       None,
            "po_no":              None,
            "so_no":              None,
            "dn_no":              None,
            "invoice_no":         None,
            "payment_reference":  None,
            "amount":             None,
            "currency":           None,
            "payment_type":       None,
            "mode_of_payment":    None,
            "party_type":         None,
            "from_warehouse":     None,
            "to_warehouse":       None,
            "stock_entry_type":   None,
            "project":            None,
            "price_list":         None,
            "company":            None,
            "extra":              {},
        },
        "confidence":             0.40,   # Lower — signals fallback was used
        "ambiguities":            ambiguities,
        "has_ambiguities":        len(ambiguities) > 0,
        "risk_level":             "low",
        "requires_confirmation":  False,
        "raw_prompt":             prompt,
        "session_context":        [],
        "_fallback":              True,
        "_fallback_reason":       reason[:120],
    }


# ── Activities ────────────────────────────────────────────────────────────────

@activity.defn(name="extract_intent")
async def extract_intent(data: dict) -> dict:
    """
    Clarity Agent — Step 1.
    Parses a natural-language ERP command into a structured intent dict.
    Falls back to keyword matching if Gemini fails (never re-prompts user).
    """
    prompt          = data.get("prompt", "")
    erp_type        = data.get("erp_type", "erpnext")
    session_context = data.get("session_context", [])
    clarifications  = data.get("clarifications", [])
    project_id      = data.get("project_id", "")

    # ── Native Tool: CVS Search (async) ────────────────────────────────────────
    # Defined as async — the manual loop in _call_agentic_llm will await it correctly.
    async def _search_cvs_master_data(query: str, entity_type: str = "Item") -> list:
        """Search the company's ERP master data for Items, Customers, or Suppliers.

        Returns up to 10 matching records sorted by relevance.
        Each Item record includes: item_code, item_name, stock_uom, weight_per_unit, weight_uom.
        Use entity_type='Customer' or entity_type='Supplier' for parties.

        If 0 results are returned, retry with a shorter keyword (e.g. drop adjectives).
        """
        try:
            from shared.database.db import AsyncSessionLocal
            from shared.models.cvs_models import ContextSnapshot
            from sqlalchemy import select, text
            import uuid

            async with AsyncSessionLocal() as session:
                # 1. Resolve slug to UUID if necessary
                try:
                    uuid.UUID(project_id)
                    real_uuid = project_id
                except ValueError:
                    res = await session.execute(
                        text("SELECT id FROM projects WHERE company_slug = :slug LIMIT 1"),
                        {"slug": project_id}
                    )
                    real_uuid = res.scalar()
                    if not real_uuid:
                        logger.warning("CVS Search: Could not resolve project slug '%s'", project_id)
                        return []
                    real_uuid = str(real_uuid)

                # 2. Query CVS Snapshots
                res = await session.execute(
                    select(ContextSnapshot)
                    .where(
                        ContextSnapshot.project_id == uuid.UUID(str(real_uuid)),
                        ContextSnapshot.layer == "master_data",
                    )
                    .order_by(ContextSnapshot.version.desc())
                    .limit(1)
                )
                row = res.scalars().first()
                if not row or not row.data:
                    return []

            type_map = {
                "item": "items",
                "items": "items",
                "customer": "customers",
                "customers": "customers",
                "supplier": "suppliers",
                "suppliers": "suppliers",
                "warehouse": "warehouses",
                "warehouses": "warehouses",
                "cost center": "cost_centers",
                "cost_center": "cost_centers",
                "cost_centers": "cost_centers",
            }

            key = type_map.get(str(entity_type or "").strip().lower())
            if not key:
                # Best-effort: assume caller passed the raw snapshot key
                key = str(entity_type or "items").strip().lower()
            data_list = row.data.get(key, [])

            # ── Token-based fuzzy scoring ────────────────────────────────────
            # Split the query into individual words. Score each record by how
            # many tokens it matches in any searchable field. This way:
            #   query="spicy mango pickle" tokens=["spicy","mango","pickle"]
            #   record item_name="Spicy Mango Pickle - 500g"
            #   → all 3 tokens match → score=3 (top result)
            # A record with just "Mango Pickle" would score 2 (still returned).
            tokens = [t for t in query.lower().split() if len(t) > 2]
            if not tokens:
                tokens = [query.lower()]  # fallback for very short queries

            scored = []
            for record in data_list:
                # Build a combined searchable string from all text fields
                searchable = " ".join([
                    str(record.get("name",       "")),
                    str(record.get("item_code",  "")),
                    str(record.get("item_name",  "")),   # ← KEY FIX: human-readable name
                    str(record.get("customer_name", "")),
                    str(record.get("supplier_name", "")),
                ]).lower()

                score = sum(1 for t in tokens if t in searchable)
                if score > 0:
                    scored.append((score, record))

            # Sort by score descending, return top 10
            scored.sort(key=lambda x: x[0], reverse=True)
            results = [rec for _, rec in scored[:10]]

            logger.info(
                "CVS Tool: query='%s' entity=%s tokens=%s → %d matches",
                query, entity_type, tokens, len(results)
            )
            return results

        except Exception as e:
            logger.error("CVS Tool Search failed: %s", e)
            return []


    # Dispatcher maps tool name → real async implementation
    # (Schema is declared inside _call_agentic_llm via FunctionDeclaration
    #  in the new google-genai SDK — no stub Python function needed here)
    tool_dispatcher = {
        "search_cvs_master_data": _search_cvs_master_data,
    }

    activity.heartbeat("Parsing intent with Agentic Gemini")

    llm_prompt = _build_extract_prompt(prompt, erp_type, session_context, clarifications)

    try:
        from containers.os.clarity_agent.schema_builder import (
            build_allowed_entity_types,
            guess_intent_meta,
            normalise_intent_dict,
        )
        from llm_router import invoke_agentic_loop
        _intent_id_hint, _doctype_hint = guess_intent_meta(prompt)
        allowed_entity_types = build_allowed_entity_types(_doctype_hint)

        result = await invoke_agentic_loop(
            prompt=llm_prompt,
            tool_dispatcher=tool_dispatcher,
            schema=_IntentSchema,
            allowed_entity_types=allowed_entity_types,
            model_name=os.getenv("CLARITY_MODEL", "gpt-4o-mini"),
        )

        result = normalise_intent_dict(result, prompt=prompt, erp_type=erp_type, session_context=session_context)
        result.setdefault("confidence", 0.9)
        result.setdefault("risk_level", "low")
        result.setdefault("requires_confirmation", False)

        # Entities defaults
        ent = result.setdefault("entities", {})
        for k in ["customer","supplier","items","transaction_date","delivery_date",
                  "due_date","posting_date","po_no","so_no","dn_no","invoice_no",
                  "payment_reference","amount","currency","payment_type",
                  "mode_of_payment","party_type","from_warehouse","to_warehouse",
                  "stock_entry_type","project","price_list","company","extra"]:
            ent.setdefault(k, [] if k == "items" else ({} if k == "extra" else None))

        conf  = result.get("confidence", 0)
        n_amb = len(result.get("ambiguities", []))

        activity.logger.info(
            "extract_intent: intent=%s  doctype=%s  confidence=%.2f  ambiguities=%d",
            result.get("intent_id"), result.get("target_doctype"), conf, n_amb,
        )
        try:
            if result.get("has_ambiguities") and OS_CLARITY_AMBIGUITY_TOTAL is not None:
                OS_CLARITY_AMBIGUITY_TOTAL.labels(source="llm").inc()
        except Exception:
            pass
        return result

    except Exception as e:
        activity.logger.error("extract_intent failed: %s — using keyword fallback", e)
        try:
            if OS_CLARITY_FALLBACK_TOTAL is not None:
                OS_CLARITY_FALLBACK_TOTAL.labels(erp_type=str(erp_type or "unknown")).inc()
        except Exception:
            pass
        fallback = _fallback_intent(prompt, erp_type, str(e))
        fallback["raw_prompt"] = prompt
        fallback["erp_type"] = erp_type
        fallback["session_context"] = session_context
        from containers.os.clarity_agent.schema_builder import normalise_intent_dict
        fallback = normalise_intent_dict(fallback, prompt=prompt, erp_type=erp_type, session_context=session_context)

        # Best-effort: use CVS tool to detect common misclassification (item mistaken as customer/supplier)
        try:
            entities = fallback.get("entities") or {}
            party = entities.get("customer") or entities.get("supplier")
            items = entities.get("items") or []

            if party and isinstance(party, str) and (not isinstance(items, list) or len(items) == 0):
                cust_hits = await _search_cvs_master_data(party, "Customer")
                supp_hits = await _search_cvs_master_data(party, "Supplier")
                item_hits = await _search_cvs_master_data(party, "Item")

                # If it doesn't exist as a party but does exist as an item, force a helpful clarification
                if (not cust_hits and not supp_hits) and item_hits:
                    top = item_hits[0] or {}
                    hint = (
                        top.get("item_code")
                        or top.get("name")
                        or top.get("item_name")
                        or party
                    )
                    if entities.get("customer") == party:
                        entities["customer"] = None
                    if entities.get("supplier") == party:
                        entities["supplier"] = None
                    fallback["entities"] = entities
                    fallback["ambiguities"] = [{
                        "field": "items",
                        "question": (
                            f"Did you mean the item '{hint}'? "
                            "Please provide the customer/supplier name and the quantity for each item."
                        ),
                        "required": True,
                    }]
                    fallback["has_ambiguities"] = True
                    fallback["confidence"] = min(float(fallback.get("confidence") or 0.4), 0.35)
        except Exception as cvs_e:
            activity.logger.warning("fallback CVS classification skipped: %s", cvs_e)

        try:
            if fallback.get("has_ambiguities") and OS_CLARITY_AMBIGUITY_TOTAL is not None:
                OS_CLARITY_AMBIGUITY_TOTAL.labels(source="fallback").inc()
        except Exception:
            pass

        return fallback


@activity.defn(name="resolve_ambiguity")
async def resolve_ambiguity(data: dict) -> dict:
    """
    Clarity Agent — Step 2 (optional, only called if ambiguities exist).
    Re-parses with the user's clarification answer folded in.
    Falls back gracefully — never crashes the pipeline.
    """
    original_prompt  = data.get("original_prompt", "")
    partial_intent   = data.get("partial_intent", {})
    clarification_qa = data.get("clarification_qa", [])
    erp_type         = partial_intent.get("erp_type", "erpnext")

    activity.heartbeat("Resolving ambiguity")

    qa_str = "\n".join(
        f"  Q: {qa.get('question','')}\n  A: {qa.get('answer','')}"
        for qa in clarification_qa
    )
    prompt = f"""You are an ERP command parser. The user clarified their command.
Update the intent JSON with the new information.

Original command: {original_prompt}
Clarifications:
{qa_str}

Return the complete updated intent JSON (same structure as before).
Preserve intent_id, target_doctype, and existing entities (customer, supplier, items)
unless the user explicitly changed them in the clarification answers.
Return ONLY valid JSON:"""

    try:
        raw = await _call_llm(prompt)
        if not isinstance(raw, dict):
            raw = {}
        from containers.os.clarity_agent.schema_builder import (
            fill_intent_gaps_from_partial,
            normalise_intent_dict,
        )
        merged = fill_intent_gaps_from_partial(raw, partial_intent)
        result = normalise_intent_dict(
            merged,
            prompt=original_prompt,
            erp_type=erp_type,
            session_context=[],
        )
        result = fill_intent_gaps_from_partial(result, partial_intent)
        result = normalise_intent_dict(
            result,
            prompt=original_prompt,
            erp_type=erp_type,
            session_context=[],
        )

        activity.logger.info(
            "resolve_ambiguity: intent=%s  confidence=%.2f",
            result.get("intent_id"), result.get("confidence", 0),
        )
        return result

    except Exception as e:
        activity.logger.warning("resolve_ambiguity failed (%s) — using partial intent", e)
        # Clear ambiguities so pipeline doesn't loop forever
        partial_intent["ambiguities"]    = []
        partial_intent["has_ambiguities"] = False
        return partial_intent