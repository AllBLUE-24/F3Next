"""Persist unified gap_items on the session readiness assessment row."""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from containers.implementation.is_common.gap_report import merge_gap_item_dicts


async def append_session_gap_items(
    session_id: str,
    new_items: List[Dict[str, Any]],
    *,
    preflight_blocks: Optional[List[Dict[str, Any]]] = None,
) -> None:
    """Merge gap_items into latest ISDataReadinessAssessment.gap_report."""
    if not new_items and not preflight_blocks:
        return

    from sqlalchemy import select
    from shared.database.db import AsyncSessionLocal
    from shared.models.is_models import ISDataReadinessAssessment
    from containers.implementation.is_common.gap_report import gap_from_preflight_block

    block_items = [
        gap_from_preflight_block(b).to_dict()
        for b in (preflight_blocks or [])
        if isinstance(b, dict)
    ]
    merged_new = merge_gap_item_dicts(new_items, block_items)

    async with AsyncSessionLocal() as db:
        stmt = (
            select(ISDataReadinessAssessment)
            .where(ISDataReadinessAssessment.session_id == uuid.UUID(session_id))
            .order_by(ISDataReadinessAssessment.created_at.desc())
            .limit(1)
        )
        row = (await db.execute(stmt)).scalar_one_or_none()
        if not row:
            return

        report = dict(row.gap_report or {})
        existing = list(report.get("gap_items") or [])
        report["gap_items"] = merge_gap_item_dicts(existing, merged_new)
        if preflight_blocks:
            prior = list(report.get("mapping_preflight_blocks") or [])
            report["mapping_preflight_blocks"] = prior + [
                b for b in preflight_blocks if isinstance(b, dict)
            ]
        row.gap_report = report
        await db.commit()


async def persist_mapping_gap_chat(
    session_id: str,
    preflight_blocks: List[Dict[str, Any]],
) -> None:
    """Surface mapping preflight blocks in the chat thread."""
    if not preflight_blocks:
        return

    from containers.implementation.file_io.persist_chat_message import save_chat_message

    lines: List[str] = []
    for block in preflight_blocks:
        doctype = block.get("doctype") or "record"
        source = block.get("source_file") or "file"
        missing = ", ".join(block.get("missing_fields") or []) or "required fields"
        lines.append(f"**{doctype}** not mapped from `{source}` — missing {missing}.")

    content = (
        "Mapping could not complete for some doctypes:\n"
        + "\n".join(f"• {line}" for line in lines)
        + "\n\nUpload corrected data or fix column headers, then re-run mapping."
    )
    await save_chat_message(
        session_id,
        "validate",
        "system",
        content,
        message_type="gap_blocking",
        message_metadata={"preflight_blocks": preflight_blocks},
    )
