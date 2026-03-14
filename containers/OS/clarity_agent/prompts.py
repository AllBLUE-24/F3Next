"""
containers/OS/clarity_agent/prompts.py

Builds the LLM prompts for the Clarity Agent.
All prompt content is derived from the loaded KnowledgeBase — never hardcoded.

Two prompts:
  1. SYSTEM PROMPT — injected once, contains full intent taxonomy + extraction rules
  2. USER TEMPLATE  — per-request, includes prompt + session context + today's date
  3. RESOLVE PROMPT — secondary call to merge a clarification answer into a partial intent
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from containers.OS.clarity_agent.kb_loader import kb


# ─── Output schema description ────────────────────────────────────────────────

_OUTPUT_SCHEMA = """
Return ONLY a valid JSON object. No markdown. No explanation. No backticks.

{
  "intent_id":        "create_sales_order",       // Must be one of the intent IDs listed above
  "category":         "create",                    // create / read / update / delete / search / submit / cancel / report / bulk
  "target_doctype":   "Sales Order",               // ERPNext doctype name
  "action":           "create",                    // create / get / update / submit / cancel / delete / search / report
  "confidence":       0.92,                        // 0.0 to 1.0
  "risk_level":       "low",                       // low / medium / high / critical
  "entities": {
    "customer":       "ABC Industries",            // null if not mentioned
    "supplier":       null,
    "items": [
      {
        "item_code":  "Product-001",               // exact user-provided name
        "qty":        100,                         // number or null
        "rate":       500,                         // number or null
        "uom":        "Nos",                       // unit if mentioned
        "warehouse":  null
      }
    ],
    "transaction_date": null,                      // ISO yyyy-mm-dd or null
    "delivery_date":    "2025-03-31",              // ISO yyyy-mm-dd or null
    "po_no":            null,
    "amount":           null,
    "payment_type":     null,
    "mode_of_payment":  null,
    "from_warehouse":   null,
    "to_warehouse":     null,
    "extra":            {}                         // any other fields mentioned
  },
  "ambiguities": [                                 // empty array if none
    {
      "field":    "items",
      "question": "What items should be included?",
      "required": true
    }
  ],
  "has_ambiguities": false
}
"""


# ─── System prompt builder ────────────────────────────────────────────────────

def build_system_prompt() -> str:
    """
    Build the full system prompt for the Clarity Agent.
    Called once when the worker starts, cached by the caller.
    Rebuilding on every request is unnecessary — KB doesn't change at runtime.
    """
    _kb = kb()

    return f"""You are the Clarity Agent for an ERP Operating System.
Your job: parse a user's natural language ERP command and extract structured intent + entities.

══════════════════════════════════════════════════════════════════════
INTENT TAXONOMY (all valid intent_ids and their meanings)
══════════════════════════════════════════════════════════════════════
{_kb.intent_summary_for_prompt()}

══════════════════════════════════════════════════════════════════════
ABBREVIATION EXPANSIONS (resolve before classification)
══════════════════════════════════════════════════════════════════════
{_kb.abbreviation_summary_for_prompt()}
Examples: "create SO" → create_sales_order, "record payment" → create_payment_entry

══════════════════════════════════════════════════════════════════════
ENTITY EXTRACTION RULES
══════════════════════════════════════════════════════════════════════
ITEMS:
  - Pattern: [qty] [uom?] [item_name/code] [at/@ rate?]
  - Multiple items separated by comma, semicolon, or "and"
  - "100 Product-001 at ₹500" → item_code=Product-001, qty=100, rate=500
  - "50 units of Widget-X" → item_code=Widget-X, qty=50
  - Keep item_code exactly as the user wrote it (case-preserving)

CUSTOMER/SUPPLIER:
  - "for ABC Industries" → customer=ABC Industries
  - "to supplier XYZ" → supplier=XYZ
  - "from customer Sharma Trading" → customer=Sharma Trading

DATES:
  - "by March 15" / "deliver by end of month" → resolve to ISO date using today's date
  - "today" → today's date, "tomorrow" → tomorrow's date
  - "end of month" → last day of current month
  - Always output as yyyy-mm-dd

PAYMENT INFERENCE (from contextual rules):
  - "received from customer" / "payment from" → payment_type=Receive, party_type=Customer
  - "paid to supplier" / "payment to" → payment_type=Pay, party_type=Supplier
  - "via NEFT" → mode_of_payment=Bank Transfer - NEFT
  - "via cash" → mode_of_payment=Cash
  - "via UPI" → mode_of_payment=UPI

STOCK ENTRY INFERENCE:
  - "transfer from WH-A to WH-B" → stock_entry_type=Material Transfer
  - "issue from WH-Main" → stock_entry_type=Material Issue
  - "receive into WH-Main" → stock_entry_type=Material Receipt

══════════════════════════════════════════════════════════════════════
AMBIGUITY RULES
══════════════════════════════════════════════════════════════════════
Flag as ambiguous (required=true) when:
  - A REQUIRED entity for the intent is completely missing
  - Customer/item name has no match possible (pure ambiguity, not a lookup failure)

Flag as ambiguous (required=false) when:
  - An optional field would improve quality but can be defaulted

NEVER ask about:
  - transaction_date (default = today)
  - company (comes from company profile)
  - currency (comes from company profile)

══════════════════════════════════════════════════════════════════════
CONFIDENCE SCORING
══════════════════════════════════════════════════════════════════════
0.85 – 1.0 : All required entities present and unambiguous
0.65 – 0.84: Required entities present, minor optional fields missing
0.50 – 0.64: Missing 1 required entity OR intent unclear
0.00 – 0.49: Multiple possible intents OR critical info missing

══════════════════════════════════════════════════════════════════════
CONTEXTUAL RESOLUTION (session memory)
══════════════════════════════════════════════════════════════════════
If session context is provided:
  - "same customer" / "the same one" → resolve from previous turn's customer entity
  - "add 50 more" → resolve as update or continuation of previous intent
  - Pronouns like "it", "them", "that order" → resolve to last mentioned document

══════════════════════════════════════════════════════════════════════
OUTPUT FORMAT
══════════════════════════════════════════════════════════════════════
{_OUTPUT_SCHEMA}

CRITICAL RULES:
  - intent_id MUST be one of the listed intent IDs. Never invent new ones.
  - If you cannot determine the intent, return intent_id="unknown" with confidence=0.0
  - items must always be a list (even if only one item)
  - All numeric values (qty, rate, amount) must be numbers, never strings
  - Null fields must be null (not empty string, not 0)
  - Do not wrap output in ```json``` blocks
"""


# ─── Per-request user prompt builder ─────────────────────────────────────────

def build_user_prompt(
    prompt:           str,
    session_context:  Optional[list[dict]] = None,
    clarification_so_far: Optional[list[dict]] = None,
) -> str:
    """
    Build the user-turn message for a specific command.
    Includes today's date and session memory for contextual resolution.
    """
    today = date.today().isoformat()
    parts: list[str] = [f"Today's date: {today}"]

    if session_context:
        ctx_lines = []
        for turn in session_context[-4:]:   # Last 4 turns max
            role    = turn.get("role", "")
            content = turn.get("content", "")
            if role == "user":
                ctx_lines.append(f"  User: {content}")
            elif role == "assistant":
                preview = content[:120] + "..." if len(content) > 120 else content
                ctx_lines.append(f"  Assistant: {preview}")
        if ctx_lines:
            parts.append("Session context (recent conversation):\n" + "\n".join(ctx_lines))

    if clarification_so_far:
        qa_lines = []
        for qa in clarification_so_far:
            qa_lines.append(f"  Q: {qa.get('question', '')}")
            qa_lines.append(f"  A: {qa.get('answer', '')}")
        if qa_lines:
            parts.append("Clarifications already collected:\n" + "\n".join(qa_lines))

    parts.append(f"User command: {prompt}")

    return "\n\n".join(parts)


# ─── Resolve-ambiguity prompt ─────────────────────────────────────────────────

def build_resolve_prompt(
    original_prompt:    str,
    partial_intent:     dict,
    clarification_qa:   list[dict],
) -> str:
    """
    Used by the resolve_ambiguity activity.
    Takes the partial intent + Q&A so far and asks the LLM to produce
    an updated StructuredIntent with the new information merged in.
    """
    today = date.today().isoformat()
    qa_text = "\n".join(
        f"  Q: {qa.get('question', '')}\n  A: {qa.get('answer', '')}"
        for qa in clarification_qa
    )

    return f"""Today's date: {today}

Original user command: {original_prompt}

Partial intent extracted so far:
{partial_intent}

Clarifications collected:
{qa_text}

Merge the clarification answers into the partial intent.
Produce a complete, updated StructuredIntent JSON.
Apply the same extraction rules as before.
Return ONLY the JSON — no explanation, no backticks.
"""


# ─── Cached system prompt ─────────────────────────────────────────────────────

_CACHED_SYSTEM_PROMPT: str | None = None


def get_system_prompt() -> str:
    """Return the system prompt, building it once and caching for the process lifetime."""
    global _CACHED_SYSTEM_PROMPT
    if _CACHED_SYSTEM_PROMPT is None:
        _CACHED_SYSTEM_PROMPT = build_system_prompt()
    return _CACHED_SYSTEM_PROMPT