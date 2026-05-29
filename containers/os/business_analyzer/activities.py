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
from shared.os_field_semantics import (
    business_fields_missing,
    filter_missing_for_doctype,
    is_master_create_doctype,
    tier1_mandatory_missing,
)
from shared.os_metrics import (
    OS_BUSINESS_CLARIFICATION_TRIGGERED,
    OS_LLM_REASONING_JSON_FAILURE_TOTAL,
    OS_RAG_CACHE_HIT_TOTAL,
    OS_RAG_CACHE_MISS_TOTAL,
    OS_RAG_CHUNKS_RETRIEVED,
    OS_RAG_QUERY_TOTAL,
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


def _tier1_analysis(doctype: str, entities: dict, *, query_used: str = "") -> dict[str, Any]:
    missing, applied = tier1_mandatory_missing(doctype, entities)
    return {
        "missing_critical_fields": missing,
        "applied_defaults": applied,
        "confidence": 1.0 if not missing else 0.5,
        "ready_for_planning": len(missing) == 0,
        "rag": {"apqc": 0, "erpnext": 0, "f3iche": 0},
        "query_used": query_used,
        "analysis_mode": "tier1_only",
    }


def _business_analysis(
    doctype: str,
    entities: dict,
    profile: dict,
    *,
    query_used: str = "",
) -> dict[str, Any]:
    """Transactional docs: only ask user-facing fields (party, items, optional dates)."""
    missing, applied = business_fields_missing(doctype, entities, profile)
    tier1 = [m for m in missing if int(m.get("tier", 1)) == 1]
    return {
        "missing_critical_fields": missing,
        "applied_defaults": applied,
        "confidence": 1.0 if not tier1 else 0.85,
        "ready_for_planning": len(tier1) == 0,
        "rag": {"apqc": 0, "erpnext": 0, "f3iche": 0},
        "query_used": query_used,
        "analysis_mode": "business_fields",
    }


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


@activity.defn(name="analyze_business_requirements")
async def analyze_business_requirements(intent: dict, context: dict) -> dict:
    """
    RAG-powered analysis to identify missing *business-critical* fields.
    Master-data creates use Tier1 KB only (no item/pricing LLM questions).
    """
    doctype = str((intent or {}).get("target_doctype") or "").strip() or "Unknown"
    action = str((intent or {}).get("action") or "create")
    entities = (intent or {}).get("entities") or {}
    if not isinstance(entities, dict):
        entities = {}

    profile = (context or {}).get("company_profile") or {}
    f3iche_id = profile.get("f3_niche_id") or ""

    query_text = (
        f"{doctype} {action} business requirements critical fields. "
        "mandatory information common mistakes and defaults."
    )

    if is_master_create_doctype(doctype) and action == "create":
        return _tier1_analysis(doctype, entities, query_used=query_text)

    # Sales/purchase transactions: never ask for ERP-internal fields (naming_series, rates, etc.)
    if action == "create":
        return _business_analysis(doctype, entities, profile, query_used=query_text)

    top_k = 8
    apqc_chunks = await _rag_retrieve(query_text, kb_source_prefix="apqc_pcf", top_k=top_k)
    erpnext_chunks = await _rag_retrieve(query_text, kb_source_prefix="erpnext_docs", top_k=top_k)

    f3iche_chunks: list[str] = []
    if f3iche_id:
        f3iche_prefix = f"f3iche_{f3iche_id}"
        f3iche_chunks = await _rag_retrieve(query_text, kb_source_prefix=f3iche_prefix, top_k=min(6, top_k))

    if not apqc_chunks and not erpnext_chunks and not f3iche_chunks:
        return _business_analysis(doctype, entities, profile, query_used=query_text)

    today = date.today().isoformat()
    apqc_block = "\n\n".join(apqc_chunks[:3])
    erp_block = "\n\n".join(erpnext_chunks[:3])
    f3_block = "\n\n".join(f3iche_chunks[:2])

    reasoning_prompt = f"""
You are a senior ERP consultant.
Today's date: {today}

User intent (current structured extraction):
DocType: {doctype}
Action: {action}
Entities provided: {json.dumps(entities, ensure_ascii=False)}

Authoritative sources:

[Layer 1: APQC PCF]
{apqc_block}

[Layer 2: ERPNext Docs]
{erp_block}

[Layer 3: Company Context (F3iche/CVS)]
Company: {profile.get('company_name') or profile.get('default_company') or 'Unknown'}
Default currency: {profile.get('default_currency')}
Default price list: {profile.get('default_price_list')}
Known customers: {len((profile.get('entity_registry') or {}).get('known_customers') or [])}
Known items: {len((profile.get('entity_registry') or {}).get('known_items') or [])}
F3iche chunks (if any):
{f3_block}

Task:
Based on APQC standards and ERPNext documentation, identify which *critical business fields* are missing from this intent.

Rules:
- ONLY ask for fields that apply to DocType "{doctype}".
- NEVER ask for ERP-internal fields: naming_series, conversion_rate, selling_price_list,
  price_list_currency, plc_conversion_rate, currency, company, order_type, status.
  Those are filled from company profile automatically.
- Only ask the user for: customer/supplier (if missing), items/qty (if missing),
  or optional delivery/schedule date (tier 2, user may say skip).
- Do NOT copy example field names unless they apply to this DocType.
- Only ask for fields that materially change business correctness.
- Use tiers:
  Tier 1 (MUST ASK): cannot proceed safely without this.
  Tier 2 (SUGGEST DEFAULT): business-critical but can propose a default (ask user to confirm/override).
  Tier 3 (OPTIONAL): can safely omit.
- If no critical fields are missing, return an empty missing_critical_fields array and ready_for_planning=true.

Output ONLY valid JSON with this shape (field names must be valid for {doctype} only):
{{
  "missing_critical_fields": [],
  "applied_defaults": [
    {{"field": "transaction_date", "value": "{today}", "reason": "default"}}
  ],
  "confidence": 1.0,
  "ready_for_planning": true
}}
"""

    try:
        from langchain_core.messages import HumanMessage

        resp = await invoke_smart_llm(
            [HumanMessage(content=reasoning_prompt)],
            temperature=0.2,
            max_output_tokens=1200,
            task_type="complex",
        )
        parsed = _safe_json_loads(getattr(resp, "content", "") or "")
        if not parsed:
            try:
                if OS_LLM_REASONING_JSON_FAILURE_TOTAL is not None:
                    OS_LLM_REASONING_JSON_FAILURE_TOTAL.labels(activity="analyze_business_requirements").inc()
            except Exception:
                pass
            raise ValueError("LLM did not return valid JSON")

        if not isinstance(parsed.get("missing_critical_fields"), list):
            parsed["missing_critical_fields"] = []
        if not isinstance(parsed.get("applied_defaults"), list):
            parsed["applied_defaults"] = []
        parsed.setdefault("confidence", 0.0)

        raw_missing = parsed.get("missing_critical_fields") or []
        filtered = filter_missing_for_doctype(doctype, raw_missing)
        parsed["missing_critical_fields"] = filtered
        parsed["ready_for_planning"] = len(filtered) == 0
        parsed["analysis_mode"] = "llm_rag_filtered"
    except Exception as e:
        logger.warning("analyze_business_requirements: LLM reasoning failed: %s", e)
        parsed = _business_analysis(doctype, entities, profile, query_used=query_text)
        parsed["analysis_mode"] = "business_fields_llm_fallback"

    parsed["rag"] = {"apqc": len(apqc_chunks), "erpnext": len(erpnext_chunks), "f3iche": len(f3iche_chunks)}
    parsed["query_used"] = query_text

    try:
        if OS_BUSINESS_CLARIFICATION_TRIGGERED is not None:
            missing = parsed.get("missing_critical_fields") or []
            if isinstance(missing, list):
                for m in missing:
                    if isinstance(m, dict):
                        tier = str(m.get("tier") or 1)
                        OS_BUSINESS_CLARIFICATION_TRIGGERED.labels(doctype=doctype, tier=tier).inc()
    except Exception:
        pass

    return parsed
