"""
containers/OS/analysis_planner/activities.py

Temporal activity for the Analysis Planner.
Registered on: os-analyze-queue (and os-main-queue for routing)

Translates a Natural Language query into an ERPNext REST API GET endpoint
and provides aggregation instructions for the Data Analyst agent.
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
        response = await invoke_smart_llm([HumanMessage(content=prompt)], temperature=0.1, max_output_tokens=_MAX_TOKENS)
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


def _build_analysis_prompt(prompt: str, doctype_hint: str) -> str:
    today = date.today().isoformat()
    return f"""You are an ERPNext Data Analyst and API expert. Today is {today}.
Translate the user's natural language analysis query into an ERPNext data-fetching plan.
Return ONLY valid JSON. No markdown.

RULES:
1. `queries`: A list of API calls needed. Usually just one.
2. `doctype`: Infer the correct ERPNext doctype if the hint is "Document" or "Unknown". 
   - Revenue/Sales -> "Sales Invoice" or "Sales Order"
   - Expenses/Purchases -> "Purchase Invoice"
   - Inventory -> "Bin" or "Stock Ledger Entry"
3. `filters`: To get valid financial data, you often need `["docstatus", "=", 1]` (submitted documents only).
4. `fields`: Include the fields needed for aggregation! If the user wants "Revenue by Customer", you MUST request ["name", "grand_total", "customer"].
5. `aggregation`: A short string instructing a Python script on how to process the data (e.g., "sum(grand_total) group by customer").
6. `chart_type`: Choose one: "bar", "pie", "line", "metric", or null.

USER QUERY: "{prompt}"
DOCTYPE HINT: "{doctype_hint}"

JSON FORMAT:
{{
  "queries": [
    {{
      "doctype": "Sales Invoice",
      "filters": [["docstatus", "=", 1]],
      "fields": ["name", "posting_date", "grand_total", "customer"],
      "limit": 1000
    }}
  ],
  "aggregation": "sum(grand_total) grouped by customer",
  "time_range": "This Month",
  "chart_type": "bar"
}}
"""

def _fallback_analysis_plan(doctype: str) -> dict:
    """If LLM fails, grab recent documents to attempt basic analysis."""
    return {
        "queries": [
            {
                "doctype": doctype if doctype and doctype not in ("Document", "Unknown") else "Sales Order",
                "filters": [],
                "fields": ["name", "creation", "grand_total", "status"],
                "limit": 500
            }
        ],
        "aggregation": "count records",
        "time_range": "recent",
        "chart_type": "metric"
    }

@activity.defn(name="plan_analysis")
async def plan_analysis(data: dict) -> dict:
    """
    Receives intent_dict and context. Returns a payload_bundle 
    that the Execution Agent can run as a GET request, plus analysis metadata.
    """
    intent_dict = data.get("intent_dict", {})
    prompt      = intent_dict.get("raw_prompt", "")
    doctype     = intent_dict.get("target_doctype", "Document")

    activity.heartbeat("Planning analysis queries")

    llm_prompt = _build_analysis_prompt(prompt, doctype)
    
    try:
        analysis_plan = await _call_llm(llm_prompt)
    except Exception as e:
        activity.logger.warning("Analysis planner LLM failed (%s) — using fallback", e)
        analysis_plan = _fallback_analysis_plan(doctype)

    queries = analysis_plan.get("queries", [])
    if not queries:
        queries = _fallback_analysis_plan(doctype)["queries"]

    steps = []
    for idx, query in enumerate(queries, start=1):
        q_doctype = query.get("doctype", "Sales Order")
        q_filters = query.get("filters", [])
        q_fields  = query.get("fields", ["name", "creation"])
        if "name" not in q_fields:
            q_fields.insert(0, "name")
        q_limit   = query.get("limit", 1000)

        # Build the URL-encoded query string for ERPNext
        endpoint = f"/api/resource/{urllib.parse.quote(q_doctype)}?"
        if q_filters:
            endpoint += f"filters={urllib.parse.quote(json.dumps(q_filters))}&"
        endpoint += f"fields={urllib.parse.quote(json.dumps(q_fields))}&"
        endpoint += f"limit_page_length={q_limit}"

        steps.append({
            "step_number": idx,
            "action":      "analyze_fetch",
            "doctype":     q_doctype,
            "endpoint":    endpoint,
            "http_method": "GET",
            "payload":     {} # GET requests don't need a body
        })

    activity.logger.info(
        "plan_analysis: ✅ Planned %d queries (Aggregation: %s)", 
        len(steps), analysis_plan.get("aggregation", "none")
    )

    # Return in the format the Execution Agent expects
    return {
        "steps": steps,
        "analysis_meta": {
            "aggregation": analysis_plan.get("aggregation"),
            "time_range":  analysis_plan.get("time_range"),
            "chart_type":  analysis_plan.get("chart_type")
        },
        "risk_level": "low",
        "requires_confirmation": False
    }