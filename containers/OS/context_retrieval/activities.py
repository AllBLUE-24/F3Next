"""
containers/OS/context_retrieval/activities.py

Temporal activities for the Context Retrieval Agent.
Registered on: os-context-queue

Activity:
  retrieve_context — assembles the context bundle from KB + DB for a given intent

Context bundle shape (output):
  {
    "intent":            dict,  ← passed through unchanged
    "company_profile":   dict,  ← KB-12 profile (credentials + defaults)
    "doctype_schema":    dict,  ← KB-07 schema for target_doctype
    "module_context":    dict,  ← KB-02 module entry for target_doctype's module
    "related_doctypes":  list,  ← KB-07/02 related doc types
    "business_rules":    list,  ← KB-06 (stub for now — returns [])
    "erp_credentials":   dict,  ← extracted from company_profile (URL + keys)
    "defaults":          dict,  ← ERPNext defaults (company, warehouse, currency, etc.)
  }

NO LLM CALL in this agent — pure data assembly.
Timeout: 30s (no LLM, just DB + file reads).

Design rules applied:
  - Never raises — always returns a valid context bundle
  - erp_credentials is kept separate from context_snapshot stored in DB
    (the activity returns full bundle; the workflow stores only context_snapshot
     which strips credentials before writing to os_commands table)
"""

from __future__ import annotations

import logging
from datetime import timedelta

from temporalio import activity 

from containers.os.context_retrieval.kb_context import context_kb
from containers.os.context_retrieval.company_profile import load_company_context

logger = logging.getLogger(__name__)


@activity.defn(name="retrieve_context")
async def retrieve_context(data: dict) -> dict:
    """
    Assemble the context bundle for a given StructuredIntent.

    Input dict keys:
      intent_dict:       dict  — StructuredIntent (from Clarity Agent output)
      company_id:        str   — project_id / company UUID
      erp_type:          str   — "erpnext"
      session_id:        str   — os_sessions.id (for cache lookup)
      cached_context:    dict  — os_sessions.company_context (may be None/stale)

    Returns:
      Full context bundle dict — never raises, uses graceful fallbacks.
    """
    intent_dict     = data.get("intent_dict", {})
    company_id      = data.get("company_id", "")
    erp_type        = data.get("erp_type", "erpnext")
    session_id      = data.get("session_id")
    cached_context  = data.get("cached_context")

    target_doctype  = intent_dict.get("target_doctype", "")
    intent_id       = intent_dict.get("intent_id", "unknown")

    activity.heartbeat("Loading company profile")

    # ── Step 1: Company profile (DB or dummy) ─────────────────────────────────
    try:
        company_profile = await load_company_context(
            project_id     = company_id,
            session_id     = session_id,
            cached_context = cached_context,
        )
    except Exception as e:
        logger.exception("company profile load failed: %s", e)
        # Import here to avoid circular import at module load
        from containers.os.context_retrieval.company_profile import _build_dummy_profile
        company_profile = _build_dummy_profile(company_id)

    activity.heartbeat("Loading doctype schema")

    # ── Step 2: Doctype schema from KB-02 + KB-07 ─────────────────────────────
    try:
        ckb            = context_kb()
        doctype_schema = ckb.doctype_schema(target_doctype) if target_doctype else {}
        module_context = ckb.module_context_for_doctype(target_doctype) if target_doctype else {}
        related_docs   = ckb.related_doctypes(target_doctype) if target_doctype else []
        workflow_str   = ckb.workflow_for_doctype(target_doctype) if target_doctype else ""
    except Exception as e:
        logger.exception("KB context load failed for doctype=%s: %s", target_doctype, e)
        doctype_schema = {}
        module_context = {}
        related_docs   = []
        workflow_str   = ""

    # ── Step 3: Business rules stub (KB-06 not yet loaded) ────────────────────
    # TODO: load kb_06_validation_rules.json here when built
    # For now return empty — Validation Agent will handle rules independently
    business_rules: list[dict] = []

    # ── Step 4: Extract credentials + defaults (separate from schema) ─────────
    erp_credentials = {
        "erp_url":    company_profile.get("erp_url", ""),
        "api_key":    company_profile.get("api_key", ""),
        "api_secret": company_profile.get("api_secret", ""),
    }

    defaults = {
        "company":          company_profile.get("default_company", ""),
        "currency":         company_profile.get("default_currency", "INR"),
        "warehouse":        company_profile.get("default_warehouse", ""),
        "price_list":       company_profile.get("default_price_list", "Standard Selling"),
        "purchase_price_list": company_profile.get("purchase_price_list", "Standard Buying"),
        "fiscal_year":      company_profile.get("fiscal_year", ""),
        "country":          company_profile.get("country", "India"),
    }

    logger.info(
        "retrieve_context: intent=%s doctype=%s company=%s profile_source=%s",
        intent_id,
        target_doctype,
        company_profile.get("company_name", "?"),
        company_profile.get("source", "?"),
    )

    return {
        # Pass-through
        "intent":           intent_dict,
        "erp_type":         erp_type,

        # Company
        "company_profile":  company_profile,   # Full profile — has credentials
        "erp_credentials":  erp_credentials,   # Extracted separately for easy access
        "defaults":         defaults,           # ERPNext defaults for payload generation

        # Schema / KB
        "doctype_schema":   doctype_schema,
        "module_context":   module_context,
        "related_doctypes": related_docs,
        "workflow":         workflow_str,

        # Validation
        "business_rules":   business_rules,    # Stub — KB-06 not loaded yet

        # Context snapshot (safe to store in DB — no credentials)
        # Workflow writes this to os_commands.context_snapshot
        "_safe_snapshot": {
            "company_name":     company_profile.get("company_name"),
            "erp_type":         erp_type,
            "target_doctype":   target_doctype,
            "module":           doctype_schema.get("module"),
            "profile_source":   company_profile.get("source"),
            "is_dummy":         company_profile.get("is_dummy", False),
        },
    }