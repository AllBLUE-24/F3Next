from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import date
from typing import Any, Optional

from temporalio import activity

from llm_router import invoke_smart_llm
from shared.context_engine.loader import Tier1Loader, retrieve_kb_chunks
from shared.embedding_generator import embedding_to_pgvector_str, generate_embedding
from shared.rag_cache import cache_get_json, cache_set_json
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
        # attempt to extract a JSON object substring
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


def _tier1_mandatory_missing(doctype: str, entities: dict) -> list[dict[str, Any]]:
    tier1, _ = Tier1Loader().load()
    fm = (tier1.get("field_mappings") or {}).get(doctype) or {}
    mandatory = fm.get("mandatory_fields") or []
    missing: list[dict[str, Any]] = []
    for field in mandatory:
        if entities.get(field) in (None, "", [], {}):
            missing.append(
                {
                    "field": field,
                    "tier": 1,
                    "question": f"Please provide `{field}` for {doctype}.",
                    "reasoning": "Tier1 schema: mandatory field missing.",
                    "suggested_default": None,
                    "apqc_reference": None,
                    "erpnext_reference": None,
                }
            )
    return missing


@activity.defn(name="analyze_business_requirements")
async def analyze_business_requirements(intent: dict, context: dict) -> dict:
    """
    RAG-powered analysis to identify missing *business-critical* fields.

    Sources:
    - Layer 1: APQC PCF (kb_source_prefix='apqc_pcf')
    - Layer 2: ERPNext docs (kb_source_prefix='erpnext_docs')
    - Layer 3: Company context (CVS + f3iche_id if available)
    """
    doctype = str((intent or {}).get("target_doctype") or "").strip() or "Unknown"
    action = str((intent or {}).get("action") or "create")
    entities = (intent or {}).get("entities") or {}
    if not isinstance(entities, dict):
        entities = {}

    profile = (context or {}).get("company_profile") or {}
    f3iche_id = profile.get("f3_niche_id") or ""

    # Query focused on business requirements, not raw field names.
    query_text = (
        f"{doctype} {action} business requirements critical fields. "
        "pricing taxes delivery dates approvals mandatory information. "
        "common mistakes and defaults."
    )

    top_k = 8

    apqc_chunks = await _rag_retrieve(query_text, kb_source_prefix="apqc_pcf", top_k=top_k)
    erpnext_chunks = await _rag_retrieve(query_text, kb_source_prefix="erpnext_docs", top_k=top_k)

    f3iche_chunks: list[str] = []
    if f3iche_id:
        # This requires seeding f3iches into kb_embeddings as kb_source like: f3iche_<id>
        f3iche_prefix = f"f3iche_{f3iche_id}"
        f3iche_chunks = await _rag_retrieve(query_text, kb_source_prefix=f3iche_prefix, top_k=min(6, top_k))

    # Guardrail: if RAG empty, fall back to Tier1 mandatory.
    if not apqc_chunks and not erpnext_chunks and not f3iche_chunks:
        missing = _tier1_mandatory_missing(doctype, entities)
        return {
            "missing_critical_fields": missing,
            "applied_defaults": [],
            "confidence": 0.0,
            "ready_for_planning": len(missing) == 0,
            "rag": {"apqc": 0, "erpnext": 0, "f3iche": 0},
            "query_used": query_text,
        }

    today = date.today().isoformat()
    # Keep prompt bounded (avoid token blowups)
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
- Only ask for fields that materially change business correctness (pricing, taxes, delivery, warehouses, payment terms, required parties/items).
- Do NOT ask for everything the database allows.
- Use tiers:
  Tier 1 (MUST ASK): cannot proceed safely without this.
  Tier 2 (SUGGEST DEFAULT): business-critical but can propose a default (ask user to confirm/override).
  Tier 3 (OPTIONAL): can safely omit.
- If Tier1 schema mandates a field, it is Tier 1.

Output ONLY valid JSON:
{{
  "missing_critical_fields": [
    {{
      "field": "items.rate",
      "tier": 2,
      "question": "You didn't specify a rate. Should I use the default price list (Standard Selling), or do you want to specify a custom rate?",
      "reasoning": "Explain in 1-2 sentences, cite APQC/ERPNext hints.",
      "suggested_default": {{"source": "company_default", "value": "Standard Selling"}},
      "apqc_reference": "optional",
      "erpnext_reference": "optional"
    }}
  ],
  "applied_defaults": [
    {{"field": "transaction_date", "value": "{today}", "reason": "default"}}
  ],
  "confidence": 0.0,
  "ready_for_planning": false
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

        # Guardrail: ensure expected keys exist
        if not isinstance(parsed.get("missing_critical_fields"), list):
            parsed["missing_critical_fields"] = []
        if not isinstance(parsed.get("applied_defaults"), list):
            parsed["applied_defaults"] = []
        parsed.setdefault("confidence", 0.0)
        parsed["ready_for_planning"] = bool(parsed.get("ready_for_planning")) and len(parsed["missing_critical_fields"]) == 0
    except Exception as e:
        logger.warning("analyze_business_requirements: LLM reasoning failed: %s", e)
        missing = _tier1_mandatory_missing(doctype, entities)
        parsed = {
            "missing_critical_fields": missing,
            "applied_defaults": [],
            "confidence": 0.0,
            "ready_for_planning": len(missing) == 0,
        }

    parsed["rag"] = {"apqc": len(apqc_chunks), "erpnext": len(erpnext_chunks), "f3iche": len(f3iche_chunks)}
    parsed["query_used"] = query_text

    # Metrics: missing critical fields (proxy for clarification triggers)
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

