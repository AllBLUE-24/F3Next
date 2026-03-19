"""
containers/OS/data_analyst/activities.py

Temporal activity for the Data Analyst.
Registered on: os-analyze-queue

Takes raw JSON from the execution agent and uses Gemini to 
aggregate the data and write a plain English summary.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re

from dotenv import load_dotenv
load_dotenv()

from temporalio import activity

logger = logging.getLogger(__name__)

_MODEL      = "gemini-flash-latest"
_MAX_TOKENS = 1500

async def _call_llm(prompt: str, max_retries: int = 3) -> dict:
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_core.messages import HumanMessage

    llm = ChatGoogleGenerativeAI(
        model=_MODEL,
        temperature=0.1,
        max_output_tokens=_MAX_TOKENS,
        google_api_key=os.getenv("GEMINI_API_KEY"),
    )

    last_err = None
    for attempt in range(1, max_retries + 1):
        try:
            response = await llm.ainvoke([HumanMessage(content=prompt)])
            raw = response.content.strip()

            cleaned = re.sub(r'^`{3}(?:json)?\s*', '', raw, flags=re.MULTILINE)
            cleaned = re.sub(r'\s*`{3}\s*$', '', cleaned, flags=re.MULTILINE).strip()

            try:
                return json.loads(cleaned)
            except json.JSONDecodeError:
                if cleaned.strip().startswith('{') and not cleaned.strip().endswith('}'):
                    cleaned += '}'
                return json.loads(cleaned)

        except Exception as e:
            is_quota = any(k in str(e).lower() for k in ['quota', 'rate', '429'])
            if is_quota and attempt < max_retries:
                await asyncio.sleep(2 ** attempt)
                continue
            last_err = e
            break

    raise ValueError(f"LLM call failed: {last_err}")


def _build_analyst_prompt(prompt: str, raw_data: list, meta: dict) -> str:
    # Cap records to avoid blowing out the LLM context window
    MAX_RECORDS = 200
    sliced_data = raw_data[:MAX_RECORDS]
    data_str    = json.dumps(sliced_data)
    
    aggregation = meta.get('aggregation', 'Summarize this data.')

    return f"""You are an Expert ERP Data Analyst.
The user asked: "{prompt}"

You have been provided with raw JSON data exported from ERPNext.
Your task is to analyze this data, calculate the totals according to '{aggregation}', and format the output.

RAW DATA (Showing {len(sliced_data)} records):
{data_str}

Return ONLY valid JSON matching this exact structure:
{{
  "summary": "A 2-4 sentence plain English answer to the user's question, mentioning key totals.",
  "key_figures": [
    {{"label": "Total Revenue", "value": "₹5,000,000"}},
    {{"label": "Document Count", "value": "45"}}
  ],
  "chart_data": [
    {{"name": "Category A", "value": 100}}
  ]
}}
"""

@activity.defn(name="analyse_data")
async def analyse_data(execution_result: dict, analysis_plan: dict, prompt: str) -> dict:
    """
    Receives raw data from execution agent, passes it to LLM for aggregation.
    """
    activity.heartbeat("Analyzing raw data")

    # 1. Safely extract all records from the ERPNext GET response
    data_records = []
    steps_results = execution_result.get("steps_results", [])
    
    for step_res in steps_results:
        data = step_res.get("data", [])
        # ERPNext GET list responses return { "data": [...] }
        if isinstance(data, dict) and "data" in data:
            data_records.extend(data["data"])
        elif isinstance(data, list):
            data_records.extend(data)

    if not data_records:
        activity.logger.warning("Data Analyst received empty data set.")
        return {
            "summary": "No data was found matching your criteria.",
            "key_figures": [],
            "chart_data": []
        }

    # 2. Build and call LLM
    meta = analysis_plan.get("analysis_meta", {})
    llm_prompt = _build_analyst_prompt(prompt, data_records, meta)
    
    try:
        analysis_result = await _call_llm(llm_prompt)
        activity.logger.info("analyse_data: ✅ Generated summary successfully.")
        return analysis_result
    except Exception as e:
        activity.logger.error("analyse_data failed: %s", e)
        return {
            "summary": f"I retrieved {len(data_records)} records, but encountered an error while summarizing them.",
            "key_figures": [{"label": "Records Found", "value": str(len(data_records))}],
            "chart_data": []
        }