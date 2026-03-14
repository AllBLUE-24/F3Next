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

# ── Profile cache TTL ──────────────────────────────────────────────────────────
PROFILE_CACHE_TTL_SECONDS = 3600   # 1 hour — after this, re-fetch from DB


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

    return {
        # Identity
        "company_id":         company_id,
        "company_name":       company,
        "erp_type":           "erpnext",
        "f3_niche_id":        None,              # Not yet determined by IS
        "is_dummy":           True,

        # ERPNext credentials — used by Execution Agent
        "erp_url":            erp_url,
        "api_key":            api_key,
        "api_secret":         api_secret,

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
        from sqlalchemy import text

        async with AsyncSessionLocal() as session:
            # Join projects + latest hook for this project
            query = text("""
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
                WHERE p.company_slug = :project_id  -- 🔴 CHANGE THIS LINE 
                ORDER BY h.created_at DESC
                LIMIT 1
            """)
            result = await session.execute(query, {"project_id": project_id})
            row = result.mappings().first()

        if not row:
            logger.warning("Project %s not found in DB", project_id)
            return None

        deployment = row["deployment_details"] or {}
        if not deployment.get("erp_url") or not deployment.get("api_key"):
            # IS hasn't deployed ERPNext yet — no credentials available
            logger.info(
                "Project %s has no deployment_details yet — IS not complete", project_id
            )
            return None

        company = row["company_name"] or deployment.get("company", "Unknown Company")

        return {
            "company_id":         str(row["project_id"]),
            "company_name":       company,
            "erp_type":           "erpnext",
            "f3_niche_id":        None,   # TODO: read from processed_config
            "is_dummy":           False,

            # ERPNext credentials from deployment_details
            "erp_url":            deployment["erp_url"],
            "api_key":            deployment["api_key"],
            "api_secret":         deployment.get("api_secret", ""),

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


# ── Session cache check ────────────────────────────────────────────────────────

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
      1. Fresh cache from os_sessions.company_context  (0 extra DB queries)
      2. Live fetch from projects + hooks tables
      3. Dummy fallback (env vars)

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
        return profile

    # ── 3. Dummy fallback ────────────────────────────────────────────────────
    dummy = _build_dummy_profile(project_id)
    logger.info(
        "company_context: using dummy profile (IS not ready) — "
        "set ERP_URL / ERP_API_KEY / ERP_API_SECRET to test against real ERPNext"
    )
    return dummy