"""
containers/OS/search_planner/activities.py

Temporal activity for the Search Planner.
Registered on: os-search-queue (and os-main-queue for routing)

Translates a Natural Language query into an ERPNext REST API GET endpoint
complete with URL-encoded filters, fields, and limits.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import urllib.parse
from datetime import date

from dotenv import load_dotenv
load_dotenv()

from temporalio import activity

logger = logging.getLogger(__name__)

_MODEL      = "gemini-flash-latest"
_MAX_TOKENS = 800

async def _call_llm(prompt: str, max_retries: int = 3) -> dict:
    from langchain_core.messages import HumanMessage
    from llm_router import invoke_smart_llm

    try:
        response = await invoke_smart_llm([HumanMessage(content=prompt)], model_name=_MODEL, temperature=0.1, max_output_tokens=_MAX_TOKENS)
        raw = response.content.strip()

        cleaned = re.sub(r'^`{3}(?:json)?\s*', '', raw, flags=re.MULTILINE)
        cleaned = re.sub(r'\s*`{3}\s*$', '', cleaned, flags=re.MULTILINE).strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            # Basic JSON repair
            if cleaned.strip().startswith('{') and not cleaned.strip().endswith('}'):
                cleaned += '}'
            return json.loads(cleaned)
    except Exception as e:
        raise ValueError(f"LLM call failed: {e}")


def _build_search_prompt(prompt: str, doctype: str) -> str:
    today = date.today().isoformat()
    return f"""You are an ERPNext Search API expert. Today is {today}.
Translate the user's natural language search query into ERPNext API parameters.
Return ONLY valid JSON. No markdown.

RULES:
1. `filters`: A list of lists. E.g., [["customer", "like", "%Stark%"], ["status", "=", "Draft"]]
2. `fields`: Always include "name". Add 3-4 other highly relevant fields for {doctype} (e.g., "customer", "grand_total", "status", "creation", "item_name").
3. `limit`: Default to 10 unless the user specifies a number (e.g., "top 5").
4. `order_by`: Default to "creation desc" to show newest first.

USER QUERY: "{prompt}"
TARGET DOCTYPE: "{doctype}"

JSON FORMAT:
{{
  "filters": [],
  "fields": ["name", "creation"],
  "limit": 10,
  "order_by": "creation desc"
}}
"""

def _fallback_search_plan(doctype: str) -> dict:
    """If LLM fails, just fetch the 10 most recent documents."""
    return {
        "filters": [],
        "fields": ["name", "creation", "modified"],
        "limit": 10,
        "order_by": "creation desc"
    }

@activity.defn(name="plan_search")
async def plan_search(data: dict) -> dict:
    """
    Receives intent_dict and context. Returns a payload_bundle 
    that the Execution Agent can run as a GET request.
    """
    intent_dict = data.get("intent_dict", {})
    prompt      = intent_dict.get("raw_prompt", "")
    doctype     = intent_dict.get("target_doctype", "Document")

    activity.heartbeat("Planning search query")

    llm_prompt = _build_search_prompt(prompt, doctype)
    
    try:
        search_params = await _call_llm(llm_prompt)
    except Exception as e:
        activity.logger.warning("Search planner LLM failed (%s) — using fallback", e)
        search_params = _fallback_search_plan(doctype)

    filters  = search_params.get("filters", [])
    fields   = search_params.get("fields", ["name", "creation"])
    if "name" not in fields:
        fields.insert(0, "name")
    limit    = search_params.get("limit", 10)
    order_by = search_params.get("order_by", "creation desc")

    # Build the URL-encoded query string for ERPNext
    endpoint = f"/api/resource/{urllib.parse.quote(doctype)}?"
    endpoint += f"filters={urllib.parse.quote(json.dumps(filters))}&"
    endpoint += f"fields={urllib.parse.quote(json.dumps(fields))}&"
    endpoint += f"limit_page_length={limit}&"
    endpoint += f"order_by={urllib.parse.quote(order_by)}"

    activity.logger.info("plan_search: ✅ Built GET endpoint for %s (Limit: %s)", doctype, limit)

    # Return in the format the Execution Agent expects
    return {
        "steps": [
            {
                "step_number": 1,
                "action":      "search",
                "doctype":     doctype,
                "endpoint":    endpoint,
                "http_method": "GET",
                "payload":     {} # GET requests don't need a body
            }
        ],
        "risk_level": "low",
        "requires_confirmation": False
    }