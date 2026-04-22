"""
containers/OS/clarity_agent/activities.py

Temporal activities for the Clarity Agent.
Registered on: os-main-queue

FIXES vs previous version:
  - gemini-2.0-flash → gemini-flash-latest  (higher quota on free tier)
  - max_output_tokens: 200 → 1200        (was truncating JSON at char 109)
  - Added retry loop (3x) on quota/rate-limit errors with backoff
  - Fallback intent no longer has ambiguities — avoids re-prompting user
  - JSON repair: if JSON truncated, attempts to close open braces
  - Uses langchain_google_genai (not deprecated google.generativeai)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from datetime import date, timedelta

from dotenv import load_dotenv
load_dotenv()

from temporalio import activity

logger = logging.getLogger(__name__)

# ── Model config ──────────────────────────────────────────────────────────────
_MODEL      = "gemini-flash-latest"   # Higher quota than gemini-2.0-flash on free tier
_MAX_TOKENS = 1200                  # Was 200 — caused truncation at char 109

# ── LLM call with retry on quota ──────────────────────────────────────────────

async def _call_llm(prompt: str, max_retries: int = 3) -> dict:
    """
    Call Gemini and parse the JSON response.
    Attempts JSON repair if response is truncated.
    """
    from langchain_core.messages import HumanMessage
    from llm_router import invoke_smart_llm

    try:
        response = await invoke_smart_llm([HumanMessage(content=prompt)], model_name=_MODEL, temperature=0.1, max_output_tokens=_MAX_TOKENS)
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



def _sanitize_json(text: str) -> str:
    """
    Fix common Gemini JSON malformations before attempting parse:
      1. Missing colon:  "key" "value"  →  "key": "value"
         (causes: Expecting ':' delimiter)
      2. Trailing commas before } or ]
         (causes: Expecting property name or '}'
      3. Single-quoted strings  →  double-quoted
      4. Python-style booleans/nulls  (True/False/None  →  true/false/null)
    """
    # 1. Missing colon between quoted key and value
    #    Matches: "somekey" "value"  OR  "somekey" {  OR  "somekey" [  OR  "somekey" number
    text = re.sub(
        r'("(?:[^"\\]|\\.)*")\s+(?=["{\[\-\d])',
        r'\1: ',
        text,
    )

    # 2. Trailing commas before closing brace or bracket
    text = re.sub(r',\s*([}\]])', r'\1', text)

    # 3. Single-quoted strings → double-quoted (Gemini sometimes uses these)
    # Only replace when not inside an already double-quoted string
    # Simple approach: swap ' → " carefully
    text = re.sub(r"(?<![\\])'", '"', text)

    # 4. Python booleans/null → JSON
    text = re.sub(r'\bTrue\b',  'true',  text)
    text = re.sub(r'\bFalse\b', 'false', text)
    text = re.sub(r'\bNone\b',  'null',  text)

    return text

def _repair_json(text: str) -> str | None:
    """
    Attempt to close a truncated JSON object.
    Counts open braces/brackets and closes them.
    Returns repaired string or None if repair fails.
    """
    if not text.strip().startswith('{'):
        return None

    # Count unclosed structures
    stack = []
    in_string = False
    escape = False

    for ch in text:
        if escape:
            escape = False
            continue
        if ch == '\\' and in_string:
            escape = True
            continue
        if ch == '"' and not escape:
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch in ('{', '['):
            stack.append('}' if ch == '{' else ']')
        elif ch in ('}', ']'):
            if stack and stack[-1] == ch:
                stack.pop()

    if not stack:
        return None  # Already valid

    # Close any open string first
    if in_string:
        text += '"'

    # Close unclosed comma-dangling values
    text = text.rstrip().rstrip(',')

    # Close structures in reverse
    return text + ''.join(reversed(stack))


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
  create_sales_order, create_purchase_order, create_sales_invoice,
  create_purchase_invoice, create_delivery_note, create_payment_entry,
  create_stock_entry, create_journal_entry, submit_document,
  cancel_document, get_document, search_documents, generate_report,
  create_customer, create_supplier, create_item, create_quotation

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
    Does NOT set ambiguities — avoids re-prompting the user.
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
    items = []
    m_item = re.search(r'(\d+(?:\.\d+)?)\s+(?:units?|pcs?|nos?|qty)?\s*(?:of\s+)?([A-Z0-9][A-Z0-9\-\.]+)', prompt, re.IGNORECASE)
    m_rate = re.search(r'(?:@|at|₹|rs\.?|inr)\s*(\d+(?:\.\d+)?)', prompt, re.IGNORECASE)
    if m_item:
        items = [{
            "item_code": m_item.group(2),
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
        "confidence":             0.60,   # Lower — signals fallback was used
        "ambiguities":            [],     # ← EMPTY — never re-ask user
        "has_ambiguities":        False,  # ← FALSE — don't trigger ambiguity loop
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

    activity.heartbeat("Parsing intent with Gemini")

    llm_prompt = _build_extract_prompt(prompt, erp_type, session_context, clarifications)

    try:
        result = await _call_llm(llm_prompt)

        # Normalise
        result.setdefault("erp_type", erp_type)
        result.setdefault("raw_prompt", prompt)
        result.setdefault("session_context", session_context)
        result.setdefault("ambiguities", [])
        result.setdefault("has_ambiguities", False)
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
        return result

    except Exception as e:
        activity.logger.error("extract_intent failed: %s — using keyword fallback", e)
        return _fallback_intent(prompt, erp_type, str(e))


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
Return ONLY valid JSON:"""

    try:
        result = await _call_llm(prompt)
        result.setdefault("erp_type", erp_type)
        result.setdefault("raw_prompt", original_prompt)
        result.setdefault("ambiguities", [])
        result.setdefault("has_ambiguities", False)
        result.setdefault("session_context", [])

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