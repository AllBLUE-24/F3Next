"""
Resolve ERPNext adapter for IS activities from Project.deployment_details.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Optional, Tuple

logger = logging.getLogger(__name__)


async def resolve_is_erp_adapter(
    project_id: str,
    *,
    erpnext_base_url: str = "",
    erpnext_api_key: str = "",
    log=None,
) -> Tuple[Optional[str], Any]:
    """
    Build adapter for IS validate/import/readiness.

    Returns ``(base_url, adapter)`` or ``(None, None)`` when credentials missing.
    """
    log = log or logger
    from shared.database.db import AsyncSessionLocal
    from shared.erp_adapters.registry import get_adapter
    from shared.models.core import Project
    from sqlalchemy import select

    base_url = (erpnext_base_url or "").rstrip("/")
    api_token = erpnext_api_key or ""
    verify_ssl = True
    allow_insecure_ssl = True

    if project_id:
        try:
            async with AsyncSessionLocal() as db:
                stmt = select(Project).where(Project.id == uuid.UUID(project_id))
                res = await db.execute(stmt)
                project = res.scalar_one_or_none()
                if project and project.deployment_details:
                    details = project.deployment_details
                    if not base_url:
                        base_url = (details.get("site_url", "") or "").rstrip("/")
                    if not api_token:
                        dk = details.get("api_key", "")
                        ds = details.get("api_secret", "")
                        if dk and ds:
                            api_token = f"{dk}:{ds}"
                    v_ssl = details.get("verify_ssl")
                    if v_ssl is not None:
                        verify_ssl = str(v_ssl).lower() not in ("false", "0", "no")
                    a_ssl = details.get("allow_insecure_ssl")
                    if a_ssl is not None:
                        allow_insecure_ssl = str(a_ssl).lower() not in ("false", "0", "no")
        except Exception as e:
            log.warning("resolve_is_erp_adapter: project lookup failed: %s", e)

    if not base_url or not api_token or ":" not in api_token:
        return None, None

    profile = {
        "erp_type": "erpnext",
        "erp_url": base_url,
        "api_key": api_token.split(":")[0],
        "api_secret": api_token.split(":")[1],
        "verify_ssl": verify_ssl,
        "allow_insecure_ssl": allow_insecure_ssl,
    }
    try:
        return base_url, get_adapter(profile)
    except Exception as e:
        log.warning("resolve_is_erp_adapter: get_adapter failed: %s", e)
        return base_url, None
