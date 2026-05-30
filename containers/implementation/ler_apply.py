"""
Apply LER to IS mapped payloads before validate/import (foundation/is-brain).
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Set IS_USE_LER_VALIDATE=0 to disable LER on validate path (pilot rollback)
def ler_validate_enabled() -> bool:
    return os.getenv("IS_USE_LER_VALIDATE", "1").strip().lower() not in (
        "0", "false", "no", "off",
    )


async def apply_ler_to_session_mapped_data(
    *,
    project_id: str,
    company_slug: str,
    mapped_data: dict[str, dict[str, Any]],
    s3,
    r2_keys_by_doctype: dict[str, str],
    known_link_fields: Optional[dict[str, str]] = None,
    company_abbr: str = "",
    log=None,
) -> dict[str, Any]:
    """
    Resolve links on in-memory mapped payloads and persist rewritten rows to R2.
    """
    log = log or logger
    if not ler_validate_enabled():
        return {"skipped": True, "reason": "IS_USE_LER_VALIDATE disabled"}

    from shared.entity_resolution.is_adapter import resolve_is_erp_adapter
    from shared.entity_resolution.rows import resolve_all_mapped_payloads

    base_url, adapter = await resolve_is_erp_adapter(project_id, log=log)
    if not adapter:
        log.info("LER validate: no ERP adapter — skipping link resolution")
        return {"skipped": True, "reason": "no_adapter"}

    report = await resolve_all_mapped_payloads(
        adapter,
        mapped_data,
        known_link_fields=known_link_fields or {},
        preferred_abbr=company_abbr or None,
        log=log,
    )

    for doctype, payload in mapped_data.items():
        r2_key = r2_keys_by_doctype.get(doctype)
        if not r2_key:
            continue
        try:
            s3.put_object(
                Bucket="clean-data",
                Key=r2_key,
                Body=json.dumps(payload, indent=2, default=str).encode("utf-8"),
                ContentType="application/json",
            )
            log.info("LER: updated R2 payload for %s → %s", doctype, r2_key)
        except Exception as e:
            log.warning("LER: failed to write R2 for %s: %s", doctype, e)

    report["skipped"] = False
    report["erp_base_url"] = base_url
    return report
