"""
Derive Agent — Temporal activities for deriving prerequisite records when the
target structure requires a doctype but no input file mapped it.

Initial implementation is conservative:
- Only produces minimal draft records for a small set of doctypes.
- Always emits missing_information for anything that cannot be derived safely.
"""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from temporalio import activity

from shared.database.db import AsyncSessionLocal
from shared.models.is_models import ISTargetStructure, ISMappedData
from shared.models.is_status import NodeStatusEnvelope


@dataclass
class DeriveRequiredRecordsInput:
    session_id: str
    project_id: str
    company_slug: str = "unknown"


@activity.defn(name="derive_required_records")
async def derive_required_records(inp: DeriveRequiredRecordsInput) -> Any:
    """
    Reads latest target structure and mapped data pointers.
    Writes draft derived payloads to R2 under derived_payloads/{doctype}.json.
    """

    activity.logger.info("▶ derive_required_records started | session=%s", inp.session_id)

    target: Optional[ISTargetStructure] = None
    mapped_doctypes: set[str] = set()

    from sqlalchemy import select

    try:
        async with AsyncSessionLocal() as session:
            t = await session.execute(
                select(ISTargetStructure)
                .where(ISTargetStructure.session_id == uuid.UUID(inp.session_id))
                .order_by(ISTargetStructure.created_at.desc())
                .limit(1)
            )
            target = t.scalars().first()

            m = await session.execute(
                select(ISMappedData.target_doctype)
                .where(ISMappedData.session_id == uuid.UUID(inp.session_id))
                .where(ISMappedData.total_rows > 0)
            )
            mapped_doctypes = {r[0] for r in m}
    except Exception as e:
        return NodeStatusEnvelope.failed(
            errors=[{"code": "DERIVE_READ_FAILED", "message": "Failed to read target structure or mapped data", "details": {"error": str(e)}}]
        )

    setup_steps = (target.setup_steps or []) if target else []
    must_create = [s for s in setup_steps if isinstance(s, dict) and s.get("action") == "must_create"]

    missing: List[str] = []
    derived: Dict[str, Any] = {"derived": {}, "missing_doctypes": []}

    # Minimal derivation example: BOM drafts derived from Work Orders if BOM missing.
    if any(s.get("doctype") == "BOM" for s in must_create) and "BOM" not in mapped_doctypes:
        if "Work Order" in mapped_doctypes:
            try:
                from shared.r2_client import r2_read_json, r2_write_json

                slug = inp.company_slug or "unknown"
                wo_key = f"{slug}/{inp.project_id}/mappings/mapped_payloads/Work Order.json"
                wo_payload = await r2_read_json(wo_key, bucket="clean-data") or {}
                wo_records = wo_payload.get("records", []) if isinstance(wo_payload, dict) else []

                items = sorted({r.get("production_item") for r in wo_records if isinstance(r, dict) and r.get("production_item")})
                bom_records = []
                for it in items:
                    bom_records.append(
                        {
                            "item": it,
                            "quantity": 1,
                            "items": [],
                            "_draft": True,
                            "_draft_reason": "Derived from Work Orders; components unknown",
                        }
                    )

                out_key = f"{slug}/{inp.project_id}/derived_payloads/BOM.json"
                await r2_write_json(out_key, {"doctype": "BOM", "records": bom_records}, bucket="clean-data")
                derived["derived"]["BOM"] = {"count": len(bom_records), "r2_path": out_key}
                missing.append("BOM components are unknown; upload BOM/components file or provide recipe rules.")
            except Exception as e:
                missing.append(f"Could not derive BOM drafts: {e}")
        else:
            missing.append("Target structure requires BOM but there is no Work Order data to derive from.")

    # Generic coverage: list must-create doctypes that have no mapped data yet.
    for s in must_create:
        dt = s.get("doctype")
        if dt and dt not in mapped_doctypes and dt not in derived["derived"]:
            derived["missing_doctypes"].append(dt)
            missing.append(f"Missing required doctype data: {dt} (must_create) — no mapped payload present.")

    primary = {
        "derived": derived.get("derived", {}),
        "missing_doctypes": derived.get("missing_doctypes", []),
    }

    activity.logger.info("✅ derive_required_records done | derived=%s missing=%d", list(primary["derived"].keys()), len(primary["missing_doctypes"]))

    if primary["missing_doctypes"]:
        return NodeStatusEnvelope.partial(primary_result=primary, missing_information=missing)
    return NodeStatusEnvelope.success(primary_result=primary)

