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

from shared.os_metrics import OS_READINESS_BLOCK_TOTAL

_ITEMS_REQUIRED_DOCTYPES = {
    "Sales Order", "Sales Invoice", "Delivery Note",
    "Purchase Order", "Purchase Invoice", "Purchase Receipt",
    "Stock Entry", "Quotation",
}
_SALES_DOCTYPES_REQUIRE_CUSTOMER = {"Sales Order", "Sales Invoice", "Delivery Note", "Quotation"}
_PURCHASE_DOCTYPES_REQUIRE_SUPPLIER = {"Purchase Order", "Purchase Invoice", "Purchase Receipt"}


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

    # ── Step 2: Doctype schema from KB + Context Engine (Tier1/2 + CVS) ───────
    try:
        ckb = context_kb()
        doctype_schema = ckb.doctype_schema(target_doctype) if target_doctype else {}
        module_context = ckb.module_context_for_doctype(target_doctype) if target_doctype else {}
        related_docs = ckb.related_doctypes(target_doctype) if target_doctype else []
        workflow_str = ckb.workflow_for_doctype(target_doctype) if target_doctype else ""

        f3iche_id = company_profile.get("f3_niche_id") or data.get("f3iche_id") or ""
        from shared.context_engine import get_context_engine

        pc = await get_context_engine().get_context(
            project_id=str(company_id),
            f3iche_id=f3iche_id,
            layers=["master_data"],
            include_tier3=False,
        )
        graph_dt = (pc.tier2_merged_graph.get("doctypes") or {}).get(target_doctype, {})
        if graph_dt:
            doctype_schema = {**doctype_schema, "f3iche_graph_overlay": graph_dt}
        md = pc.cvs.get("master_data")
        if isinstance(md, dict) and md:
            doctype_schema["cvs_master_data_keys"] = list(md.keys())[:24]
    except Exception as e:
        logger.exception("KB / context engine load failed for doctype=%s: %s", target_doctype, e)
        doctype_schema = {}
        module_context = {}
        related_docs = []
        workflow_str = ""

    # ── Step 3: Business rules stub (KB-06 not yet loaded) ────────────────────
    # TODO: load kb_06_validation_rules.json here when built
    # For now return empty — Validation Agent will handle rules independently
    business_rules: list[dict] = []

    # ── Step 4: Extract credentials + defaults (separate from schema) ─────────
    erp_credentials = {
        "erp_url":            company_profile.get("erp_url", ""),
        "api_key":            company_profile.get("api_key", ""),
        "api_secret":         company_profile.get("api_secret", ""),
        "verify_ssl":         company_profile.get("verify_ssl", True),
        "allow_insecure_ssl": company_profile.get("allow_insecure_ssl", True),
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

    link_cache: dict[str, list[str]] = {}
    if erp_credentials.get("erp_url") and erp_credentials.get("api_key") and not company_profile.get("is_dummy"):
        try:
            from shared.erp_adapters.registry import get_adapter
            from shared.os_field_semantics import resolve_company_for_payload

            adapter = get_adapter(company_profile)
            rows = await adapter.list_records("Company", fields=["name"], limit=20)
            names = [str(r.get("name", "")).strip() for r in rows if r.get("name")]
            if names:
                link_cache["Company"] = names
                resolved = resolve_company_for_payload(
                    company_profile.get("default_company") or company_profile.get("company_name"),
                    {"company_profile": company_profile, "link_cache": link_cache, "defaults": defaults},
                )
                if resolved:
                    company_profile["erp_resolved_company"] = resolved
                    defaults["company"] = resolved
        except Exception as e:
            logger.warning("link_cache Company fetch failed for project %s: %s", company_id, e)

    logger.info(
        "retrieve_context: intent=%s doctype=%s company=%s profile_source=%s",
        intent_id,
        target_doctype,
        company_profile.get("company_name", "?"),
        company_profile.get("source", "?"),
    )

    # ── Readiness hint (purely informational; workflow may choose to block) ──
    readiness_blocker = None
    readiness_reason = None
    try:
        registry = company_profile.get("entity_registry", {}) if isinstance(company_profile, dict) else {}
        known_items = (registry.get("known_items") or []) if isinstance(registry, dict) else []
        known_customers = (registry.get("known_customers") or []) if isinstance(registry, dict) else []
        known_suppliers = (registry.get("known_suppliers") or []) if isinstance(registry, dict) else []

        if company_profile.get("is_dummy") and not company_profile.get("dummy_allowed", False):
            readiness_reason = "dummy_profile_disallowed"
            readiness_blocker = "ERP credentials are not configured yet (Implementation System not complete)."
        elif target_doctype in _ITEMS_REQUIRED_DOCTYPES and not known_items:
            readiness_reason = "no_items_in_cvs"
            readiness_blocker = "No Items found in CVS master_data for this company yet."
        elif target_doctype in _SALES_DOCTYPES_REQUIRE_CUSTOMER and not known_customers:
            readiness_reason = "no_customers_in_cvs"
            readiness_blocker = "No Customers found in CVS master_data for this company yet."
        elif target_doctype in _PURCHASE_DOCTYPES_REQUIRE_SUPPLIER and not known_suppliers:
            readiness_reason = "no_suppliers_in_cvs"
            readiness_blocker = "No Suppliers found in CVS master_data for this company yet."

        if readiness_reason and OS_READINESS_BLOCK_TOTAL is not None:
            OS_READINESS_BLOCK_TOTAL.labels(reason=readiness_reason).inc()
    except Exception:
        pass

    return {
        # Pass-through
        "intent":           intent_dict,
        "erp_type":         erp_type,

        # Company
        "company_profile":  company_profile,   # Full profile — has credentials
        "erp_credentials":  erp_credentials,   # Extracted separately for easy access
        "defaults":         defaults,           # ERPNext defaults for payload generation
        "link_cache":       link_cache,         # Live ERP link options (Company, …)

        # Schema / KB
        "doctype_schema":   doctype_schema,
        "module_context":   module_context,
        "related_doctypes": related_docs,
        "workflow":         workflow_str,

        # Validation
        "business_rules":   business_rules,    # Stub — KB-06 not loaded yet

        # Readiness hint for orchestration
        "_readiness_blocker": readiness_blocker,
        "_readiness_reason": readiness_reason,

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