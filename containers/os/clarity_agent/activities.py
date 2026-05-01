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
from typing import List, Optional

from dotenv import load_dotenv
load_dotenv()

from pydantic import BaseModel
from temporalio import activity

logger = logging.getLogger(__name__)

# ── Intent Pydantic schema (used for response_schema in Phase 2) ──────────────

class _Item(BaseModel):
    item_code: str
    qty: float
    uom: Optional[str] = None
    rate: Optional[float] = None
    warehouse: Optional[str] = None

class _Entities(BaseModel):
    customer:        Optional[str]        = None
    supplier:        Optional[str]        = None
    items:           List[_Item]          = []
    transaction_date: Optional[str]       = None
    delivery_date:   Optional[str]        = None
    due_date:        Optional[str]        = None
    posting_date:    Optional[str]        = None
    amount:          Optional[float]      = None
    currency:        Optional[str]        = None
    payment_type:    Optional[str]        = None
    mode_of_payment: Optional[str]        = None
    from_warehouse:  Optional[str]        = None
    to_warehouse:    Optional[str]        = None
    stock_entry_type: Optional[str]       = None

class _IntentSchema(BaseModel):
    intent_id:            str
    action:               str
    target_doctype:       str
    confidence:           float         = 0.9
    risk_level:           str           = "low"
    requires_confirmation: bool         = False
    has_ambiguities:      bool          = False
    ambiguities:          List[str]     = []
    entities:             _Entities     = _Entities()

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

async def _call_agentic_llm(
    prompt: str,
    tools: list = None,
    tool_dispatcher: dict = None,
) -> dict:
    """
    Two-phase agentic loop using google-genai SDK.

    Phase 1 — Tool Loop:
      Run freely with function calling. No response_mime_type (avoids conflicts
      with tool calling). Collect all search results into `collected_results`.

    Phase 2 — Structured Extraction:
      Dedicated call with NO tools, response_mime_type='application/json',
      and response_schema=_IntentSchema. The API guarantees a perfectly
      formatted JSON object — the fallback parser is never needed.
    """
    from google import genai
    from google.genai import types as gt
    from llm_router import api_keys, _is_sidelined

    model_name = "gemini-2.5-flash"
    available_keys = [k for k in api_keys if not _is_sidelined(model_name, k)]
    if not available_keys:
        available_keys = api_keys
    if not available_keys:
        raise ValueError("No Gemini API keys available")

    client = genai.Client(api_key=available_keys[0])
    has_tools = bool(tool_dispatcher)

    # ── Tool declaration ───────────────────────────────────────────────────────
    genai_tools = None
    if has_tools:
        genai_tools = [gt.Tool(function_declarations=[
            gt.FunctionDeclaration(
                name="search_cvs_master_data",
                description=(
                    "Search ERP master data for Items, Customers, or Suppliers. "
                    "Returns up to 10 records. Each Item includes: item_code, "
                    "item_name, stock_uom, weight_per_unit, weight_uom. "
                    "Retry with a shorter keyword if 0 results are returned."
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "query":       {"type": "string"},
                        "entity_type": {"type": "string", "enum": ["Item", "Customer", "Supplier"]},
                    },
                    "required": ["query"],
                },
            )
        ])]

    # ═══════════════════════════════════════════════════════════════════════════
    # PHASE 1 — Tool Loop (no JSON enforcement, no MIME type)
    # ═══════════════════════════════════════════════════════════════════════════
    contents = [gt.Content(role="user", parts=[gt.Part(text=prompt)])]
    collected_results: list[dict] = []   # accumulated for Phase 2 context

    tool_cfg = gt.GenerateContentConfig(
        system_instruction = (
            "You are the F3Next Clarity Agent. Search ERP master data using "
            "search_cvs_master_data before forming any intent. "
            "Retry with shorter keywords if 0 results. "
            "Never guess an item_code or customer name."
        ),
        tools             = genai_tools,
        temperature       = 0.1,
        max_output_tokens = _MAX_TOKENS,
    )

    for _iter in range(5):
        try:
            resp = await client.aio.models.generate_content(
                model=model_name, contents=contents, config=tool_cfg,
            )
        except Exception as e:
            raise ValueError(f"Phase 1 generate_content failed (iter {_iter}): {e}")

        candidate = resp.candidates[0] if resp.candidates else None
        if not candidate:
            raise ValueError("No candidates in Phase 1 response")

        fn_calls = [
            p.function_call
            for p in candidate.content.parts
            if p.function_call is not None
        ]

        if not fn_calls or not has_tools:
            break   # model is done calling tools — proceed to Phase 2

        # Execute tool calls
        contents.append(candidate.content)
        response_parts = []
        for fc in fn_calls:
            fn_name = fc.name
            fn_args = dict(fc.args)
            logger.info("[Clarity Agent] Tool call: %s(%s)", fn_name, fn_args)

            dispatcher_fn = tool_dispatcher.get(fn_name)
            if dispatcher_fn:
                try:
                    fn_result = await dispatcher_fn(**fn_args)
                except Exception as e:
                    logger.error("Tool '%s' raised: %s", fn_name, e)
                    fn_result = {"error": str(e)}
            else:
                fn_result = {"error": f"Tool '{fn_name}' not found"}

            logger.info(
                "[Clarity Agent] Tool '%s' returned %d result(s)",
                fn_name, len(fn_result) if isinstance(fn_result, list) else 1,
            )
            collected_results.append({
                "tool": fn_name, "query": fn_args, "results": fn_result,
            })
            response_parts.append(gt.Part(
                function_response=gt.FunctionResponse(
                    name=fn_name, response={"result": fn_result},
                )
            ))

        contents.append(gt.Content(role="tool", parts=response_parts))

    # ═══════════════════════════════════════════════════════════════════════════
    # PHASE 2 — Structured JSON Extraction (guaranteed output)
    # Separate call: no tools, response_mime_type + response_schema enforced.
    # ═══════════════════════════════════════════════════════════════════════════

    # Build a compact summary of what the tools found
    if collected_results:
        lines = []
        for tr in collected_results:
            res = tr["results"]
            lines.append(f"Searched: {tr['query']}")
            if isinstance(res, list):
                for r in res[:5]:
                    lines.append(
                        f"  item_code={r.get('item_code','?')}  "
                        f"item_name={r.get('item_name','?')}  "
                        f"stock_uom={r.get('stock_uom','?')}  "
                        f"weight_per_unit={r.get('weight_per_unit','?')}"
                    )
            else:
                lines.append(f"  {res}")
        tool_context = "\n".join(lines)
    else:
        tool_context = "No master data was searched."

    extraction_prompt = (
        f"ERP SEARCH RESULTS:\n{tool_context}\n\n"
        f"ORIGINAL USER COMMAND: {prompt}\n\n"
        "RULES:\n"
        "- item_code MUST be the exact code from the search results. Never invent one.\n"
        "- If the user said '40 kg' but stock_uom is 'Nos' and weight_per_unit is 0.5, "
        "set qty = 40 / 0.5 = 80.\n"
        "- Set confidence >= 0.95 when item_code confirmed by search.\n"
        "- Produce the structured intent JSON now."
    )

    extraction_sys = (
        "You are an ERP intent extraction engine. "
        "Given search results and a user command, produce the structured intent. "
        "Output ONLY the JSON object matching the required schema."
    )

    try:
        ext_resp = await client.aio.models.generate_content(
            model    = model_name,
            contents = [gt.Content(role="user", parts=[gt.Part(text=extraction_prompt)])],
            config   = gt.GenerateContentConfig(
                system_instruction = extraction_sys,
                temperature        = 0.1,
                max_output_tokens  = _MAX_TOKENS,
                response_mime_type = "application/json",
                response_schema    = _IntentSchema,
            ),
        )
    except Exception as e:
        raise ValueError(f"Phase 2 structured extraction failed: {e}")

    raw = ext_resp.text
    if not raw:
        raise ValueError("Phase 2 returned empty response")

    # Strip any stray markdown fences (even with MIME enforcement, models sometimes leak them)
    cleaned = re.sub(r'^```(?:json)?\s*', '', raw, flags=re.MULTILINE)
    cleaned = re.sub(r'\s*```\s*$', '', cleaned, flags=re.MULTILINE).strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        sanitized = _sanitize_json(cleaned)
        try:
            return json.loads(sanitized)
        except json.JSONDecodeError:
            pass
        repaired = _repair_json(sanitized)
        if repaired:
            return json.loads(repaired)
        raise ValueError(f"Could not parse JSON from Phase 2 extraction: {cleaned[:200]}")


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
                        ContextSnapshot.project_id == real_uuid,
                        ContextSnapshot.layer == "master_data",
                    )
                    .order_by(ContextSnapshot.version.desc())
                    .limit(1)
                )
                row = res.scalars().first()
                if not row or not row.data:
                    return []

            type_map = {
                "item":     "items",
                "customer": "customers",
                "supplier": "suppliers",
            }
            key       = type_map.get(entity_type.lower(), "items")
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
        result = await _call_agentic_llm(
            llm_prompt,
            tool_dispatcher=tool_dispatcher,
        )

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