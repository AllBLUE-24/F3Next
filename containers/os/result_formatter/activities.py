"""
containers/OS/result_formatter/activities.py

Temporal activity for the Result Formatter.
Registered on: os-main-queue

Activity name: "format_result"

FIX: Migrated from deprecated google.generativeai → langchain_google_genai
     Retry on quota errors. Deterministic fallback always produces output.
     Added 404 DoesNotExistError handling and debug logging.

Input:
  execution_result: dict
  intent_dict:      dict
  original_prompt:  str

Output: str — shown in the OS chat UI
"""

from __future__ import annotations

import asyncio
import logging
import os
import re

from dotenv import load_dotenv
load_dotenv()

from temporalio import activity

logger = logging.getLogger(__name__)

_MODEL = "gemini-flash-latest"


# ── ERP error translator ──────────────────────────────────────────────────────

def _translate_erp_error(raw_error: str) -> tuple[str, str]:
    """
    Map raw ERPNext exception strings to (plain_english, suggested_action).

    ERPNext errors arrive as strings like:
      'frappe.exceptions.LinkValidationError: Could not find Row #1: Delivery Warehouse: Stores - Main'
      'frappe.exceptions.MandatoryError: [Sales Order] customer is mandatory'

    Returns a tuple of (user_facing_message, suggestion) — both plain English.
    """
    raw = raw_error or ""
    raw_lower = raw.lower()

    # ── DoesNotExistError (HTTP 404) ────────────────────────────────────────────
    if "doesnotexisterror" in raw_lower or ("404" in raw and "not found" in raw_lower):
        # Try to extract what wasn't found
        value_match = re.search(r'404.*?:\s*(\S+)', raw, re.IGNORECASE)
        if value_match:
            missing = value_match.group(1).strip()
            return (
                f"'{missing}' was not found in ERPNext.",
                f"Create '{missing}' in ERPNext first, or check if it was spelled correctly."
            )
        return (
            "The requested resource was not found in ERPNext.",
            "Check that the item, customer, or supplier exists in your ERPNext system."
        )

    # ── LinkValidationError ──────────────────────────────────────────────────
    # Pattern: "Could not find Row #N: <FieldLabel>: <Value>"
    # Pattern: "Could not find <DocType>: <Value>"
    if "linkvalidationerror" in raw_lower or "could not find" in raw_lower:
        # Try to extract field + value from "Row #N: FieldLabel: Value"
        row_match = re.search(
            r'could not find row #\d+:\s*([^:]+):\s*(.+)',
            raw, re.IGNORECASE
        )
        if row_match:
            field = row_match.group(1).strip()
            value = row_match.group(2).strip()
            return (
                f"'{value}' was not found in your ERPNext {field} list.",
                f"Check that '{value}' exists in ERPNext under {field}, "
                f"or leave the {field} field empty to use the default."
            )
        # Generic link: "Could not find DocType: Value"
        generic_match = re.search(
            r'could not find\s+([^:]+):\s*(.+)',
            raw, re.IGNORECASE
        )
        if generic_match:
            doctype = generic_match.group(1).strip()
            value   = generic_match.group(2).strip()
            return (
                f"'{value}' does not exist in {doctype}.",
                f"Make sure '{value}' is created in ERPNext before using it here."
            )
        return (
            "A linked record was not found in ERPNext.",
            "Check that all referenced customers, items, and warehouses exist in your ERPNext data."
        )

    # ── MandatoryError ───────────────────────────────────────────────────────
    # Pattern: "[DocType] field_name is mandatory"  OR  "field_name is mandatory for DocType"
    # Example: "frappe.exceptions.MandatoryError: [Customer, guruji idli]: customer_group is mandatory"
    if "mandatoryerror" in raw_lower or "is mandatory" in raw_lower:
        field_match = re.search(
            r'([a-zA-Z0-9_]+)\s+is mandatory',
            raw, re.IGNORECASE
        )
        field_name = field_match.group(1).replace("_", " ").title() if field_match else "a required field"
        return (
            f"'{field_name}' is required but was not provided.",
            f"Please include '{field_name}' in your command, "
            f"or configure a default value for it in ERPNext."
        )

    # ── DuplicateEntryError ──────────────────────────────────────────────────
    if "duplicateentryerror" in raw_lower or "duplicate entry" in raw_lower or "already exists" in raw_lower:
        doc_match = re.search(r'["\']([^"\']+)["\'] already exists', raw, re.IGNORECASE)
        doc_name  = f" '{doc_match.group(1)}'" if doc_match else ""
        return (
            f"A document{doc_name} with these details already exists.",
            "Check for an existing record in ERPNext before creating a new one."
        )

    # ── ValidationError (generic Frappe) ────────────────────────────────────
    if "validationerror" in raw_lower:
        # Try to extract the human part after the exception class
        msg_match = re.search(r'validationerror[:\s]+(.+)', raw, re.IGNORECASE)
        msg = msg_match.group(1).strip() if msg_match else raw
        # Strip any Python traceback noise (anything after a newline)
        msg = msg.split("\n")[0].strip()
        return (
            f"ERPNext rejected this entry: {msg}",
            "Review the highlighted fields and correct the values."
        )

    # ── PermissionError ──────────────────────────────────────────────────────
    if "permissionerror" in raw_lower or "not permitted" in raw_lower or "403" in raw:
        return (
            "You don't have permission to perform this action in ERPNext.",
            "Ask your ERPNext administrator to grant the required role or permission."
        )

    # ── AuthError / 401 ──────────────────────────────────────────────────────
    if "autherror" in raw_lower or "401" in raw or "invalid token" in raw_lower:
        return (
            "ERPNext rejected the API credentials.",
            "Check that ERP_API_KEY and ERP_API_SECRET in your .env are correct and not expired."
        )

    # ── TimestampMismatchError ────────────────────────────────────────────────
    if "timestampmismatch" in raw_lower:
        return (
            "This document was modified by someone else while you were working.",
            "Reload the document and try again."
        )

    # ── Fallback — clean up raw string ───────────────────────────────────────
    # Strip the Python exception class prefix (frappe.exceptions.XError: )
    cleaned = re.sub(r'^[\w.]+Error[:\s]+', '', raw, flags=re.IGNORECASE).strip()
    cleaned = cleaned.split("\n")[0].strip()  # first line only
    return (
        cleaned or "ERPNext returned an error.",
        "Check the ERPNext error log for more detail."
    )


# ── Deterministic fallback ────────────────────────────────────────────────────

def _stub_format(execution_result: dict, intent_dict: dict) -> str:
    result   = execution_result.get("result", {})
    doc_name = result.get("name", "") if isinstance(result, dict) else ""
    doctype  = intent_dict.get("target_doctype", "Document")
    action   = intent_dict.get("action", "process")
    is_stub  = isinstance(result, dict) and result.get("_stub", False)

    if execution_result.get("success"):
        suffix = " (stub — connect real ERPNext to execute)" if is_stub else ""
        return f"✅ {doctype} **{doc_name}** {action}d successfully.{suffix}"
    else:
        err = execution_result.get("error", {})
        raw_msg = err.get("message", "Unknown error") if isinstance(err, dict) else str(err)
        plain, suggestion = _translate_erp_error(raw_msg)
        return f"❌ {action.title()} {doctype} failed: {plain} {suggestion}"


# ── Prompt builder ────────────────────────────────────────────────────────────

def _build_prompt(execution_result: dict, intent_dict: dict, original_prompt: str) -> str:
    result   = execution_result.get("result", {})
    doc_name = result.get("name", "") if isinstance(result, dict) else ""
    doctype  = intent_dict.get("target_doctype", "Document")
    action   = intent_dict.get("action", "create")
    entities = intent_dict.get("entities", {})
    success  = execution_result.get("success", False)
    elapsed  = execution_result.get("execution_time_ms", 0)
    is_stub  = isinstance(result, dict) and result.get("_stub", False)

    customer  = entities.get("customer", "")
    supplier  = entities.get("supplier", "")
    party     = customer or supplier
    items     = entities.get("items", [])
    items_str = ""
    if items:
        first = items[0]
        items_str = f"{first.get('item_code','')} × {first.get('qty','')} @ ₹{first.get('rate','')}"
        if len(items) > 1:
            items_str += f" (+{len(items)-1} more)"

    if success:
        stub_note = "\nNote: Stub result — real ERPNext not yet connected." if is_stub else ""
        return f"""Write a 2-3 sentence confirmation for an ERP user. Start with ✅.
Include the document name/number prominently. Mention the party and items.
No markdown headers. Plain text only.{stub_note}

What happened:
  Action: {action} {doctype}
  Document: {doc_name or '(created)'}
  Party: {party or '(none)'}
  Items: {items_str or '(none)'}
  Time: {elapsed}ms

User's original command: "{original_prompt}"

Write ONLY the confirmation message:"""
    else:
        err = execution_result.get("error", {})
        raw_msg = err.get("message", "Unknown error") if isinstance(err, dict) else str(err)
        plain, suggestion = _translate_erp_error(raw_msg)
        return f"""Write a 2-3 sentence error message for an ERP user. Start with ❌.
Explain what went wrong in plain language. End with the suggested action.

What happened: {action} {doctype} FAILED
Plain error: {plain}
Suggestion: {suggestion}
Raw error (for context only, do NOT show to user): {raw_msg}
User's command: "{original_prompt}"

Write ONLY the error message:"""


# ── LLM call ──────────────────────────────────────────────────────────────────

async def _call_gemini(prompt: str) -> str:
    from langchain_core.messages import HumanMessage
    from llm_router import invoke_smart_llm

    response = await invoke_smart_llm(
        [HumanMessage(content=prompt)], 
        model_name=_MODEL, 
        temperature=0.3, 
        max_output_tokens=500
    )
    return response.content.strip()


# ── Main activity ──────────────────────────────────────────────────────────────

@activity.defn(name="format_result")
async def format_result(
    execution_result: dict,
    intent_dict:      dict,
    original_prompt:  str,
) -> str:
    """
    Result Formatter — final step.
    Uses Gemini to produce human-readable response.
    Falls back to template if Gemini fails — always returns a string.
    """
    doctype = intent_dict.get("target_doctype", "Document")
    action  = intent_dict.get("action", "create")

    activity.heartbeat("Formatting result")

    try:
        prompt    = _build_prompt(execution_result, intent_dict, original_prompt)
        
        # 🔴 Debug logging added here to see exactly what we're asking Gemini
        activity.logger.info("format_result: raw prompt = %s", prompt[:500].replace("\n", " | "))
        
        formatted = await _call_gemini(prompt)

        if not formatted or len(formatted.strip()) < 5:
            raise ValueError("LLM returned empty response")

        activity.logger.info(
            "format_result: ✅ %s %s → %d chars",
            action, doctype, len(formatted),
        )
        return formatted

    except Exception as e:
        activity.logger.warning("format_result: Gemini failed (%s) — using template", e)
        return _stub_format(execution_result, intent_dict)