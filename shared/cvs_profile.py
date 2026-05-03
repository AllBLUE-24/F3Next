"""
Load CVS-facing company profile from `projects` (deployment_details).

Shared between FastAPI and Temporal workers so workers never import `backend.app`.
"""

from __future__ import annotations

import logging
import uuid as uuid_lib
from typing import Any, Optional, Tuple

from sqlalchemy import select

logger = logging.getLogger(__name__)


async def load_cvs_company_profile(project_id: str) -> Tuple[str, dict[str, Any]]:
    """
    Returns (company_slug, profile_dict) including webhook_secret when present.

    Raises ValueError if project missing or ERP credentials not configured.
    """
    from shared.database.db import AsyncSessionLocal
    from shared.models.core import Project

    try:
        pid = uuid_lib.UUID(str(project_id))
    except ValueError as e:
        raise ValueError(f"Invalid project_id {project_id}") from e

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Project).where(Project.id == pid))
        project = result.scalars().first()

    if not project:
        raise ValueError(f"Project {project_id} not found")

    deployment = project.deployment_details or {}
    if not deployment.get("api_key"):
        raise ValueError(f"Project {project_id} has no ERP credentials yet (IS not complete)")

    company = project.company_name or deployment.get("company", "Unknown")
    company_slug = project.company_slug or str(project.id)

    impl = project.implementation_profile or {}
    erp_type = impl.get("erp_type") or "erpnext"

    profile: dict[str, Any] = {
        "company_id": str(project.id),
        "company_name": company,
        "company_slug": company_slug,
        "erp_type": erp_type,
        "erp_url": deployment.get("erp_url") or deployment.get("site_url", ""),
        "api_key": deployment.get("api_key", ""),
        "api_secret": deployment.get("api_secret", ""),
        "webhook_secret": deployment.get("webhook_secret", ""),
        "verify_ssl": deployment.get("verify_ssl", True),
        "allow_insecure_ssl": deployment.get("allow_insecure_ssl", True),
        "default_company": deployment.get("company", company),
        "default_currency": deployment.get("currency", "INR"),
        "default_warehouse": deployment.get("default_warehouse", ""),
        "source": "cvs_profile_loader",
    }

    return company_slug, profile


async def build_force_sync_company_profile(project_id: str) -> Tuple[str, dict[str, Any]]:
    """Payload for POST /api/cvs/force-sync — company_slug + company_profile."""
    slug, profile = await load_cvs_company_profile(project_id)
    return slug, profile
