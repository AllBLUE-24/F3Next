"""
containers/implementation/mapping_agent/live_schema.py

Live ERP schema fallback for the mapping agent.

When a doctype is NOT present in the static field_mappings.json KB, this module
fetches the authoritative schema directly from the client's ERP instance via the
ERPAdapter (adapter-agnostic — works with any ERP type registered in
shared/erp_adapters/registry.py).

Credentials are loaded exclusively from `Project.deployment_details` via
`shared.cvs_profile.load_cvs_company_profile`, which is the single, consistent
source of truth for per-project ERP credentials across the entire F3Next codebase.
No env-var credential fallbacks; those would silently target the wrong instance.

Call hierarchy:
    schema_builder.build_doctype_record_model(doctype)
        → if KB miss → live_schema.fetch_live_doctype_schema(doctype, project_id)
              → load_cvs_company_profile(project_id)  [reads deployment_details]
              → get_adapter(profile)                  [ERP-agnostic adapter]
              → adapter.get_doctype_schema(doctype)   [live API call]
              → convert raw fields → field_mappings.json format

The result is cached in-memory per (project_id, doctype) pair for the lifetime of
the worker process. Schema changes in ERPNext require a worker restart to pick up
(acceptable — field-level schema changes are rare and should be coordinated anyway).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ── In-process schema cache: (project_id, doctype) → field list ───────────────
# Keyed by project_id so different clients don't share schemas (they may have
# custom fields that differ).
_LIVE_SCHEMA_CACHE: Dict[str, List[Dict[str, Any]]] = {}


async def fetch_live_doctype_schema(
    doctype: str,
    project_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Fetch the field list for `doctype` from the project's live ERP instance.

    Args:
        doctype:    ERPNext (or other ERP) doctype name, e.g. "Work Order".
        project_id: F3Next project UUID string. Credentials are loaded from
                    Project.deployment_details in the database.
                    If None or the project has no deployment_details yet,
                    returns [] gracefully.

    Returns:
        List of field dicts in field_mappings.json format:
            [{"fieldname": str, "fieldtype": str, "mandatory": bool, "label": str,
              "options": str|None, "user_input_synonyms": [...]}, ...]
        Returns [] on any failure so callers always degrade gracefully.

    Note:
        Requires `adapter.get_doctype_schema()` to be implemented by the ERP
        adapter in use. `ERPNextAdapter` supports this via Frappe REST API.
        Other adapters may not — they will raise NotImplementedError, which is
        caught here and logged as a warning.
    """
    if not project_id:
        logger.debug("live_schema: no project_id provided — skipping live fetch for %s", doctype)
        return []

    cache_key = f"{project_id}::{doctype}"
    if cache_key in _LIVE_SCHEMA_CACHE:
        logger.debug("live_schema: cache hit for %s (project=%s)", doctype, project_id)
        return _LIVE_SCHEMA_CACHE[cache_key]

    try:
        # ── Step 1: Load project ERP credentials from deployment_details ────────
        # This is the canonical way to get per-project ERP credentials in F3Next.
        # cvs_profile.load_cvs_company_profile raises ValueError if the project
        # has no deployment_details yet (IS not complete), so we catch that below.
        from shared.cvs_profile import load_cvs_company_profile
        _, adapter_profile = await load_cvs_company_profile(project_id)

    except ValueError as e:
        # Project not found or IS not complete (no deployment_details yet).
        # This is not an error — it means we're in the mapping stage before
        # deployment has been configured. Fall back to KB-only mode.
        logger.info(
            "live_schema: skipping live fetch for %s (project=%s) — %s",
            doctype, project_id, e,
        )
        return []
    except Exception as e:
        logger.warning(
            "live_schema: failed to load credentials for project=%s: %s",
            project_id, e,
        )
        return []

    try:
        # ── Step 2: Get the ERP-agnostic adapter for this project ────────────────
        # get_adapter() reads erp_type from the profile and returns the correct
        # adapter implementation (ERPNextAdapter, SAPAdapter, etc.).
        from shared.erp_adapters.registry import get_adapter
        adapter = get_adapter(adapter_profile)

    except Exception as e:
        logger.warning(
            "live_schema: could not build adapter for project=%s erp_type=%s: %s",
            project_id, adapter_profile.get("erp_type"), e,
        )
        return []

    try:
        # ── Step 3: Fetch live schema from the ERP ───────────────────────────────
        # Adapter raises NotImplementedError if the ERP type doesn't support
        # schema introspection yet. Other adapters can add get_doctype_schema()
        # without touching this module.
        raw_fields = await adapter.get_doctype_schema(doctype)

    except NotImplementedError:
        logger.info(
            "live_schema: adapter %s does not support get_doctype_schema — "
            "falling back to KB-only for %s",
            type(adapter).__name__, doctype,
        )
        return []
    except Exception as e:
        logger.warning(
            "live_schema: ERP schema fetch failed for %s (project=%s): %s",
            doctype, project_id, e,
        )
        return []

    if not raw_fields:
        logger.info(
            "live_schema: %s returned 0 fields for %s (project=%s)",
            type(adapter).__name__, doctype, project_id,
        )
        return []

    # ── Step 4: Convert raw adapter fields → field_mappings.json format ─────────
    # The adapter returns: [{"fieldname": str, "fieldtype": str, "reqd": 0|1,
    #                        "label": str, "options": str|None, "default": any}]
    # We convert to the same shape that schema_builder.py expects from the KB so
    # the rest of the pipeline is completely unaware of where the schema came from.
    converted: List[Dict[str, Any]] = []
    for f in raw_fields:
        fname = (f.get("fieldname") or "").strip()
        label = (f.get("label") or fname).strip()
        if not fname:
            continue

        # Build a minimal synonym set: field name + label handle most real-world
        # column name variations (e.g. "production_item" + "Production Item").
        # The KB can always be enriched later with richer synonyms for common
        # doctypes — this is just a safe baseline.
        synonyms = list({
            fname,
            fname.lower(),
            fname.replace("_", " "),
            label,
            label.lower(),
            label.lower().replace(" ", "_"),
        } - {""})

        converted.append({
            "fieldname":           fname,
            "fieldtype":           f.get("fieldtype") or "Data",
            "mandatory":           bool(f.get("reqd")),
            "options":             f.get("options"),    # Link target doctype
            "default":             f.get("default"),
            "user_input_synonyms": synonyms,
        })

    _LIVE_SCHEMA_CACHE[cache_key] = converted
    logger.info(
        "live_schema: fetched %d fields for %s from %s (project=%s)",
        len(converted), doctype, type(adapter).__name__, project_id,
    )
    return converted


def clear_live_schema_cache(
    project_id: Optional[str] = None,
    doctype: Optional[str] = None,
) -> None:
    """
    Clear the in-process schema cache.

    - project_id=None, doctype=None → clear everything
    - project_id only              → clear all doctypes for that project
    - both                         → clear that specific (project, doctype) pair
    """
    global _LIVE_SCHEMA_CACHE
    if project_id is None and doctype is None:
        _LIVE_SCHEMA_CACHE.clear()
    elif doctype is None:
        keys = [k for k in _LIVE_SCHEMA_CACHE if k.startswith(f"{project_id}::")]
        for k in keys:
            del _LIVE_SCHEMA_CACHE[k]
    else:
        key = f"{project_id}::{doctype}"
        _LIVE_SCHEMA_CACHE.pop(key, None)
