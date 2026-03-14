"""
containers/OS/result_formatter/activities.py

Temporal activity for the Result Formatter.
Registered on: os-main-queue

Activity name: "format_result"

FIX: Migrated from deprecated google.generativeai → langchain_google_genai
     Retry on quota errors. Deterministic fallback always produces output.

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
        msg = err.get("message", "Unknown error") if isinstance(err, dict) else str(err)
        return f"❌ {action.title()} {doctype} failed: {msg}"


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
        msg = err.get("message", "Unknown error") if isinstance(err, dict) else str(err)
        return f"""Write a 2-3 sentence error message for an ERP user. Start with ❌.
Explain what went wrong in plain language. Suggest what to check.

What happened: {action} {doctype} FAILED
Error: {msg}
User's command: "{original_prompt}"

Write ONLY the error message:"""


# ── LLM call ──────────────────────────────────────────────────────────────────

async def _call_gemini(prompt: str) -> str:
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_core.messages import HumanMessage

    llm = ChatGoogleGenerativeAI(
        model=_MODEL,
        temperature=0.3,
        max_output_tokens=300,
        google_api_key=os.getenv("GEMINI_API_KEY"),
    )

    for attempt in range(1, 4):
        try:
            response = await llm.ainvoke([HumanMessage(content=prompt)])
            return response.content.strip()
        except Exception as e:
            is_quota = any(k in str(e).lower() for k in ['quota', 'rate', '429'])
            if is_quota and attempt < 3:
                await asyncio.sleep(2 ** attempt)
                continue
            raise


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