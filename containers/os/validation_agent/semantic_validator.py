from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import date
from typing import Any, Optional

from temporalio import activity

from llm_router import invoke_smart_llm
from shared.context_engine.loader import retrieve_kb_chunks
from shared.embedding_generator import embedding_to_pgvector_str, generate_embedding
from shared.rag_cache import cache_get_json, cache_set_json
from shared.os_metrics import (
    OS_LLM_REASONING_JSON_FAILURE_TOTAL,
    OS_RAG_CACHE_HIT_TOTAL,
    OS_RAG_CACHE_MISS_TOTAL,
    OS_RAG_CHUNKS_RETRIEVED,
    OS_RAG_QUERY_TOTAL,
    OS_SEMANTIC_VALIDATION_WARNINGS_TOTAL,
)

logger = logging.getLogger(__name__)


def _hash_query(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _safe_json_loads(raw: str) -> Optional[dict]:
    if not raw or not isinstance(raw, str):
        return None
    cleaned = raw.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"\s*```\s*$", "", cleaned, flags=re.MULTILINE).strip()
    try:
        return json.loads(cleaned)
    except Exception:
        m = re.search(r"(\{[\s\S]*\})", cleaned)
        if m:
            try:
                return json.loads(m.group(1))
            except Exception:
                return None
    return None


async def _rag_retrieve(query_text: str, *, kb_source_prefix: str, top_k: int) -> list[str]:
    cache_key = f"rag:{kb_source_prefix}:{_hash_query(query_text)}:k{top_k}"
    cached = await cache_get_json(cache_key)
    if isinstance(cached, list) and cached:
        try:
            if OS_RAG_CACHE_HIT_TOTAL is not None:
                OS_RAG_CACHE_HIT_TOTAL.labels(layer=kb_source_prefix).inc()
        except Exception:
            pass
        return [str(x) for x in cached]

    try:
        if OS_RAG_CACHE_MISS_TOTAL is not None:
            OS_RAG_CACHE_MISS_TOTAL.labels(layer=kb_source_prefix).inc()
    except Exception:
        pass

    vec = await generate_embedding(query_text)
    vec_str = embedding_to_pgvector_str(vec)
    try:
        if OS_RAG_QUERY_TOTAL is not None:
            OS_RAG_QUERY_TOTAL.labels(layer=kb_source_prefix).inc()
    except Exception:
        pass
    chunks = await retrieve_kb_chunks(vec_str, top_k=top_k, kb_source_prefix=kb_source_prefix)
    try:
        if OS_RAG_CHUNKS_RETRIEVED is not None:
            OS_RAG_CHUNKS_RETRIEVED.labels(layer=kb_source_prefix).observe(len(chunks))
    except Exception:
        pass
    await cache_set_json(cache_key, chunks)
    return chunks


@activity.defn(name="validate_business_logic")
async def validate_business_logic(payload: dict, intent: dict, context: dict) -> dict:
    """
    Semantic validation (RAG + LLM). Produces warnings (never hard errors).
    """
    doctype = str((intent or {}).get("target_doctype") or payload.get("doctype") or "").strip() or "Unknown"
    action = str((intent or {}).get("action") or "create")

    profile = (context or {}).get("company_profile") or {}
    f3iche_id = profile.get("f3_niche_id") or ""

    query_text = (
        f"{doctype} {action} common mistakes business validation pricing taxes delivery date "
        "payment terms warehouse and compliance."
    )
    top_k = 6

    try:
        apqc_chunks = await _rag_retrieve(query_text, kb_source_prefix="apqc_pcf", top_k=top_k)
        erpnext_chunks = await _rag_retrieve(query_text, kb_source_prefix="erpnext_docs", top_k=top_k)
        f3iche_chunks: list[str] = []
        if f3iche_id:
            f3iche_chunks = await _rag_retrieve(query_text, kb_source_prefix=f"f3iche_{f3iche_id}", top_k=4)
    except Exception as e:
        logger.warning("validate_business_logic: RAG retrieval failed: %s", e)
        return {"warnings": [], "confidence": 0.0, "rag": {"apqc": 0, "erpnext": 0, "f3iche": 0}}

    today = date.today().isoformat()
    apqc_block = "\n\n".join(apqc_chunks[:2])
    erp_block = "\n\n".join(erpnext_chunks[:2])
    f3_block = "\n\n".join(f3iche_chunks[:2]) if f3iche_id else ""

    prompt = f"""
You are validating an ERP payload for business correctness.
Today's date: {today}

DocType: {doctype}
Action: {action}

Payload (truncated if long):
{json.dumps(payload, ensure_ascii=False)[:4500]}

Company defaults:
- Company: {profile.get('company_name') or profile.get('default_company') or 'Unknown'}
- Default price list: {profile.get('default_price_list')}
- Country: {profile.get('country')}

[APQC PCF]
{apqc_block}

[ERPNext Docs]
{erp_block}

[F3iche]
{f3_block}

Task:
Return WARNINGS for potential business logic issues that are NOT strict schema failures.
Examples:
- rates missing/zero/suspicious
- taxes missing or likely wrong for transaction
- delivery/schedule date missing or in the past
- warehouse missing when stock item required

Output ONLY JSON:
{{
  "warnings": [
    {{
      "field": "items[0].rate",
      "message": "Rate is missing. This impacts pricing.",
      "severity": "warning",
      "suggestion": "Use default price list Standard Selling"
    }}
  ],
  "confidence": 0.0
}}
"""

    try:
        from langchain_core.messages import HumanMessage

        resp = await invoke_smart_llm(
            [HumanMessage(content=prompt)],
            temperature=0.2,
            max_output_tokens=900,
            task_type="complex",
        )
        parsed = _safe_json_loads(getattr(resp, "content", "") or "")
        if not parsed:
            try:
                if OS_LLM_REASONING_JSON_FAILURE_TOTAL is not None:
                    OS_LLM_REASONING_JSON_FAILURE_TOTAL.labels(activity="validate_business_logic").inc()
            except Exception:
                pass
            raise ValueError("LLM returned invalid JSON")
        warnings = parsed.get("warnings")
        if not isinstance(warnings, list):
            warnings = []
        parsed["warnings"] = warnings
        parsed.setdefault("confidence", 0.0)
        try:
            if OS_SEMANTIC_VALIDATION_WARNINGS_TOTAL is not None and warnings:
                OS_SEMANTIC_VALIDATION_WARNINGS_TOTAL.labels(doctype=doctype).inc(len(warnings))
        except Exception:
            pass
        parsed["rag"] = {"apqc": len(apqc_chunks), "erpnext": len(erpnext_chunks), "f3iche": len(f3iche_chunks) if f3iche_id else 0}
        return parsed
    except Exception as e:
        logger.warning("validate_business_logic: LLM reasoning failed: %s", e)
        return {"warnings": [], "confidence": 0.0, "rag": {"apqc": len(apqc_chunks), "erpnext": len(erpnext_chunks), "f3iche": len(f3iche_chunks) if f3iche_id else 0}}

