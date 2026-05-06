"""Prometheus metrics for ERP-OS (no-op if prometheus_client missing)."""

from __future__ import annotations

try:
    from prometheus_client import Counter

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
except ImportError:  # pragma: no cover
    OS_CLARITY_FALLBACK_TOTAL = None
    OS_CLARITY_AMBIGUITY_TOTAL = None
    OS_PROFILE_DUMMY_TOTAL = None
    OS_PLANNER_UNRESOLVED_LINK_TOTAL = None
    OS_VALIDATION_ERRORS_TOTAL = None
    OS_READINESS_BLOCK_TOTAL = None

