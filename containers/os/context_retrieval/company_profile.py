"""
containers/OS/context_retrieval/company_profile.py

Fetches the company profile (KB-12) for a given project.

Resolution order:
  1. os_sessions.company_context  — cached on session (fastest, 0 extra DB queries)
  2. projects + hooks tables       — build profile from live DB data
  3. DUMMY_PROFILE                 — fallback while Implementation System isn't ready

The dummy profile is configurable via env vars so you can point it at a
real ERPNext instance for OS testing without the IS pipeline being complete.

Key env vars for dummy profile:
  ERP_URL         e.g. http://localhost:8080
  ERP_API_KEY     ERPNext API key
  ERP_API_SECRET  ERPNext API secret
  ERP_COMPANY     Default company name (e.g. "Demo Company")

Profile shape (KB-12 compatible):
  {
    "company_id":         str,
    "company_name":       str,
    "erp_type":           "erpnext",
    "erp_url":            str,
    "api_key":            str,
    "api_secret":         str,
    "default_company":    str,
    "default_currency":   "INR",
    "default_warehouse":  str,
    "default_price_list": str,
    "fiscal_year":        str,
    "country":            "India",
    "required_modules":   list[str],
    "f3_niche_id":        str | null,
    "context_tags":       list[str],
    "is_dummy":           bool         ← true only for dummy profile
  }
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

from shared.os_metrics import OS_PROFILE_DUMMY_TOTAL

# ── Profile cache TTL ──────────────────────────────────────────────────────────
PROFILE_CACHE_TTL_SECONDS = 300   # 5 min — CVS keeps context fresh, so shorter TTL is fine


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


# ── Dummy profile (env-configurable) ──────────────────────────────────────────

def _build_dummy_profile(company_id: str) -> dict:
    """
    Build a realistic dummy company profile from environment variables.

    This is the fallback used while the Implementation System hasn't yet
    generated a real KB-12 profile for this company. It gives downstream
    agents (Payload Generator, Execution Agent) everything they need:
    ERP credentials + sensible defaults for a trading company.

    To use against a real ERPNext instance:
      export ERP_URL=http://localhost:8080
      export ERP_API_KEY=your_key
      export ERP_API_SECRET=your_secret
    """
    erp_url     = os.getenv("ERP_URL", "http://localhost:8080")
    api_key     = os.getenv("ERP_API_KEY", "REPLACE_WITH_REAL_KEY")
    api_secret  = os.getenv("ERP_API_SECRET", "REPLACE_WITH_REAL_SECRET")
    company     = os.getenv("ERP_COMPANY", "Demo Company")
    warehouse   = os.getenv("ERP_DEFAULT_WAREHOUSE", f"Stores - {company[:2].upper()}")
    price_list  = os.getenv("ERP_DEFAULT_PRICE_LIST", "Standard Selling")
    fiscal_year = os.getenv("ERP_FISCAL_YEAR", "2024-2025")
    verify_ssl = _env_bool("ERP_VERIFY_SSL", True)
    allow_insecure_ssl = _env_bool("ERP_ALLOW_INSECURE_SSL", True)
    dummy_allowed = _env_bool("ALLOW_DUMMY_PROFILE", False)

    return {
        # Identity
        "company_id":         company_id,
        "company_name":       company,
        "erp_type":           "erpnext",
        "f3_niche_id":        None,              # Not yet determined by IS
        "is_dummy":           True,
        "dummy_allowed":     dummy_allowed,

        # ERPNext credentials — used by Execution Agent
        "erp_url":            erp_url,
        "api_key":            api_key,
        "api_secret":         api_secret,
        "verify_ssl":         verify_ssl,
        "allow_insecure_ssl": allow_insecure_ssl,

        # ERPNext defaults — used by Payload Generator
        "default_company":    company,
        "default_currency":   "INR",
        "default_warehouse":  warehouse,
        "default_price_list": price_list,
        "purchase_price_list": "Standard Buying",
        "fiscal_year":        fiscal_year,
        "country":            "India",

        # Enabled modules — conservative trading defaults
        "required_modules": [
            "Stock",
            "Selling",
            "Buying",
            "Accounts",
        ],

        # Context tags (from IS discovery — empty for dummy)
        "context_tags": [],

        # Metadata
        "profile_version":   0,
        "fetched_at":        datetime.now(timezone.utc).isoformat(),
        "source":            "dummy_fallback",
    }


# ── Live profile fetch (from projects + hooks tables) ─────────────────────────

async def fetch_profile_from_db(
    project_id: str,
    session_id: Optional[str] = None,
) -> Optional[dict]:
    """
    Try to build a company profile from the existing DB tables.

    Sources:
      projects table:  company_name, company_slug, context_tags, deployment_details
      hooks table:     discovery answers (chat_history), extracted_tags

    deployment_details (JSONB on projects) is where the IS stores ERP credentials
    after deployment. Shape expected:
      {
        "erp_url":     "http://...",
        "api_key":     "...",
        "api_secret":  "...",
        "company":     "...",
        ...
      }

    Returns None if:
      - Project not found
      - deployment_details is empty (IS not yet complete)
    """
    try:
        from shared.database.db import AsyncSessionLocal
        import uuid as uuid_lib
        from sqlalchemy import text

        pid_uuid = None
        try:
            pid_uuid = uuid_lib.UUID(str(project_id))
        except (ValueError, TypeError):
            pid_uuid = None

        async with AsyncSessionLocal() as session:
            if pid_uuid:
                where_clause = "p.id = :pid_uuid"
            else:
                where_clause = "p.company_slug = :project_id"

            # Join projects + latest hook for this project
            query = text(f"""
                SELECT
                    p.id             AS project_id,
                    p.company_name,
                    p.company_slug,
                    p.context_tags,
                    p.deployment_details,
                    p.processed_config,
                    h.extracted_tags,
                    h.answers_health_check
                FROM projects p
                LEFT JOIN hooks h ON h.project_id = p.id
                WHERE {where_clause}
                ORDER BY h.created_at DESC
                LIMIT 1
            """)
            result = await session.execute(query, {"project_id": project_id, "pid_uuid": pid_uuid})
            row = result.mappings().first()

        if not row:
            logger.warning("Project %s not found in DB", project_id)
            return None

        deployment = row["deployment_details"] or {}

        # Derive erp_url if missing — prefer site_url (full domain), fall back to container_id
        if not deployment.get("erp_url"):
            if deployment.get("site_url"):
                deployment["erp_url"] = deployment["site_url"]
            elif deployment.get("container_id"):
                container_host = deployment["container_id"].replace("cnt_", "", 1)
                deployment["erp_url"] = f"https://{container_host}"
            if deployment.get("erp_url"):
                logger.info(
                    "Derived erp_url=%s for project %s",
                    deployment["erp_url"], project_id,
                )

        if not deployment.get("api_key"):
            # IS hasn't deployed ERPNext yet — no credentials available
            logger.info(
                "Project %s has no deployment_details yet — IS not complete", project_id
            )
            return None

        company = row["company_name"] or deployment.get("company", "Unknown Company")
        verify_ssl = deployment.get("verify_ssl")
        if verify_ssl is None:
            verify_ssl = _env_bool("ERP_VERIFY_SSL", True)

        allow_insecure_ssl = deployment.get("allow_insecure_ssl")
        if allow_insecure_ssl is None:
            allow_insecure_ssl = _env_bool("ERP_ALLOW_INSECURE_SSL", True)

        return {
            "company_id":         str(row["project_id"]),
            "company_name":       company,
            "erp_type":           "erpnext",
            "f3_niche_id":        None,   # TODO: read from processed_config
            "is_dummy":           False,
            "dummy_allowed":     _env_bool("ALLOW_DUMMY_PROFILE", False),
            "company_slug":       row.get("company_slug") or "",

            # ERPNext credentials from deployment_details
            "erp_url":            deployment["erp_url"],
            "api_key":            deployment["api_key"],
            "api_secret":         deployment.get("api_secret", ""),
            "verify_ssl":         verify_ssl,
            "allow_insecure_ssl": allow_insecure_ssl,

            # Defaults
            "default_company":    deployment.get("company", company),
            "default_currency":   deployment.get("currency", "INR"),
            "default_warehouse":  deployment.get("default_warehouse", "Stores - Main"),
            "default_price_list": deployment.get("default_price_list", "Standard Selling"),
            "purchase_price_list": "Standard Buying",
            "fiscal_year":        deployment.get("fiscal_year", "2024-2025"),
            "country":            deployment.get("country", "India"),

            # From discovery
            "required_modules":   deployment.get("modules", ["Stock", "Selling", "Buying", "Accounts"]),
            "context_tags":       row["context_tags"] or [],

            "profile_version":    1,
            "fetched_at":         datetime.now(timezone.utc).isoformat(),
            "source":             "projects_db",
        }

    except Exception as e:
        logger.exception("DB profile fetch failed for project %s: %s", project_id, e)
        return None

async def fetch_cvs_enrichment(project_id: str) -> dict:
    """
    Read the latest CVS master_data and transaction_intel snapshots from Supabase.

    Returns a dict with:
      entity_registry     — known_customers, known_items, etc. (injected into Clarity prompt)
      transaction_intel   — open orders, overdue invoices, pending actions
      cvs_version         — snapshot version numbers for logging

    Returns empty dicts if no CVS snapshot exists yet (IS not complete or CVS not seeded).
    Never raises.
    """
    import uuid
    try:
        pid = uuid.UUID(project_id)
    except ValueError:
        logger.debug("CVS enrichment skipped: project_id '%s' is not a valid UUID", project_id)
        return {"entity_registry": {}, "transaction_intel": {}, "cvs_version": {}}

    try:
        from shared.database.db import AsyncSessionLocal
        from shared.models.cvs_models import ContextSnapshot
        from sqlalchemy import select

        result_dict: dict = {
            "entity_registry":   {},
            "transaction_intel": {},
            "cvs_version":       {},
        }

        async with AsyncSessionLocal() as session:
            for layer in ["master_data", "transaction_intel"]:
                res = await session.execute(
                    select(ContextSnapshot)
                    .where(
                        ContextSnapshot.project_id == pid,
                        ContextSnapshot.layer      == layer,
                    )
                    .order_by(ContextSnapshot.version.desc())
                    .limit(1)
                )
                row = res.scalars().first()

                if row and row.data:
                    result_dict["cvs_version"][layer] = row.version

                    if layer == "master_data":
                        data = row.data
                        result_dict["entity_registry"] = {
                            "known_customers":  data.get("known_customers", []),
                            "known_suppliers":  data.get("known_suppliers", []),
                            "known_items":      data.get("known_items", []),
                            "known_warehouses": data.get("known_warehouses", []),
                            "counts":           data.get("counts", {}),
                        }

                    elif layer == "transaction_intel":
                        result_dict["transaction_intel"] = row.data

        if result_dict["entity_registry"] or result_dict["transaction_intel"]:
            logger.info(
                "CVS enrichment loaded: customers=%d items=%d cvs_versions=%s project=%s",
                len(result_dict["entity_registry"].get("known_customers", [])),
                len(result_dict["entity_registry"].get("known_items", [])),
                result_dict["cvs_version"],
                project_id,
            )
        else:
            logger.debug("CVS enrichment: no snapshots yet for project=%s", project_id)

        return result_dict

    except Exception as e:
        logger.exception("CVS enrichment fetch failed for project=%s: %s", project_id, e)
        return {"entity_registry": {}, "transaction_intel": {}, "cvs_version": {}}


def _is_cache_fresh(company_context: dict) -> bool:
    """Return True if the cached profile is less than TTL seconds old."""
    fetched_at_str = company_context.get("fetched_at")
    if not fetched_at_str:
        return False
    try:
        fetched_at = datetime.fromisoformat(fetched_at_str)
        if fetched_at.tzinfo is None:
            fetched_at = fetched_at.replace(tzinfo=timezone.utc)
        age = (datetime.now(timezone.utc) - fetched_at).total_seconds()
        return age < PROFILE_CACHE_TTL_SECONDS
    except (ValueError, TypeError):
        return False


async def load_company_context(
    project_id: str,
    session_id: Optional[str],
    cached_context: Optional[dict],
) -> dict:
    """
    Main entry point for Context Retrieval.

    Resolution order:
      1. Fresh cache from os_sessions.company_context  (5-min TTL)
      2. Live fetch from projects + hooks tables
      3. Dummy fallback (env vars)

    After resolving the base profile, enriches it with CVS snapshot data:
      - entity_registry (known customers, items, warehouses) → injected into context bundle
      - transaction_intel (open orders, overdue invoices, pending actions)

    Always returns a valid profile dict — never raises.
    """
    # ── 1. Use cache if fresh ────────────────────────────────────────────────
    if cached_context and _is_cache_fresh(cached_context):
        logger.debug("company_context: using session cache for project %s", project_id)
        return cached_context

    # ── 2. Try live DB fetch ─────────────────────────────────────────────────
    logger.info("company_context: fetching from DB for project %s", project_id)
    profile = await fetch_profile_from_db(project_id, session_id)

    if profile:
        logger.info(
            "company_context: loaded from DB for company '%s'", profile.get("company_name")
        )
    else:
        # ── 3. Dummy fallback ────────────────────────────────────────────────
        profile = _build_dummy_profile(project_id)
        logger.info(
            "company_context: using dummy profile (IS not ready) — "
            "set ERP_URL / ERP_API_KEY / ERP_API_SECRET to test against real ERPNext"
        )
        try:
            if OS_PROFILE_DUMMY_TOTAL is not None:
                allowed = "true" if profile.get("dummy_allowed") else "false"
                OS_PROFILE_DUMMY_TOTAL.labels(allowed=allowed).inc()
        except Exception:
            pass

    # ── CVS Enrichment: inject entity_registry + transaction_intel ────────────
    # This runs regardless of whether we got a real or dummy profile.
    # If no CVS snapshot exists yet, enrichment returns empty dicts (no-op).
    cvs_data = await fetch_cvs_enrichment(project_id)
    profile["entity_registry"]   = cvs_data.get("entity_registry", {})
    profile["transaction_intel"] = cvs_data.get("transaction_intel", {})
    profile["cvs_version"]       = cvs_data.get("cvs_version", {})

    return profile
