"""Prometheus metrics for ERP-OS (no-op if prometheus_client missing)."""

from __future__ import annotations

try:
    from prometheus_client import Counter, Histogram

    OS_CLARITY_FALLBACK_TOTAL = Counter(
        "os_clarity_fallback_total",
        "Clarity agent fallback invocations (LLM failure path)",
        ["erp_type"],
    )

    OS_CLARITY_AMBIGUITY_TOTAL = Counter(
        "os_clarity_ambiguity_total",
        "Clarity agent outputs containing ambiguities",
        ["source"],
    )

    OS_PROFILE_DUMMY_TOTAL = Counter(
        "os_company_profile_dummy_total",
        "OS context retrieval returned a dummy profile",
        ["allowed"],
    )

    OS_PLANNER_UNRESOLVED_LINK_TOTAL = Counter(
        "os_planner_unresolved_link_total",
        "Planner could not resolve a mandatory Link field deterministically",
        ["doctype", "field"],
    )

    OS_VALIDATION_ERRORS_TOTAL = Counter(
        "os_validation_errors_total",
        "Validation errors emitted by rule_id",
        ["rule_id"],
    )

    OS_READINESS_BLOCK_TOTAL = Counter(
        "os_readiness_block_total",
        "OS readiness gate blocks by reason",
        ["reason"],
    )

    # ── RAG / Business Intelligence ──────────────────────────────────────────

    OS_RAG_QUERY_TOTAL = Counter(
        "os_rag_query_total",
        "RAG queries executed",
        ["layer"],
    )

    OS_RAG_CACHE_HIT_TOTAL = Counter(
        "os_rag_cache_hit_total",
        "RAG cache hits by layer",
        ["layer"],
    )

    OS_RAG_CACHE_MISS_TOTAL = Counter(
        "os_rag_cache_miss_total",
        "RAG cache misses by layer",
        ["layer"],
    )

    OS_RAG_CHUNKS_RETRIEVED = Histogram(
        "os_rag_chunks_retrieved",
        "Number of chunks retrieved per RAG query",
        ["layer"],
        buckets=(0, 1, 2, 3, 5, 8, 12, 20),
    )

    OS_BUSINESS_CLARIFICATION_TRIGGERED = Counter(
        "os_business_clarification_triggered_total",
        "Business clarification loop invoked",
        ["doctype", "tier"],
    )

    OS_SEMANTIC_VALIDATION_WARNINGS_TOTAL = Counter(
        "os_semantic_validation_warnings_total",
        "Semantic validation warnings emitted",
        ["doctype"],
    )

    OS_LLM_REASONING_JSON_FAILURE_TOTAL = Counter(
        "os_llm_reasoning_json_failure_total",
        "LLM reasoning calls that failed to return valid JSON",
        ["activity"],
    )
except ImportError:  # pragma: no cover
    OS_CLARITY_FALLBACK_TOTAL = None
    OS_CLARITY_AMBIGUITY_TOTAL = None
    OS_PROFILE_DUMMY_TOTAL = None
    OS_PLANNER_UNRESOLVED_LINK_TOTAL = None
    OS_VALIDATION_ERRORS_TOTAL = None
    OS_READINESS_BLOCK_TOTAL = None
    OS_RAG_QUERY_TOTAL = None
    OS_RAG_CACHE_HIT_TOTAL = None
    OS_RAG_CACHE_MISS_TOTAL = None
    OS_RAG_CHUNKS_RETRIEVED = None
    OS_BUSINESS_CLARIFICATION_TRIGGERED = None
    OS_SEMANTIC_VALIDATION_WARNINGS_TOTAL = None
    OS_LLM_REASONING_JSON_FAILURE_TOTAL = None

