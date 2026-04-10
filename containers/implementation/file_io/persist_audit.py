"""
File IO — persist_audit activity.

Shared helper to log entries into the is_audit_trail table.
Used by all other persistence activities for full audit tracking.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from temporalio import activity


@dataclass
class AuditEntry:
    session_id: str
    action: str
    actor: str = "system"
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    result: Optional[str] = None


@activity.defn(name="persist_audit")
async def persist_audit(entry: AuditEntry) -> str:
    """Insert a row into is_audit_trail. Returns 'ok'."""
    from shared.database.db import AsyncSessionLocal
    from shared.models.is_models import ISAuditTrail

    try:
        async with AsyncSessionLocal() as session:
            session.add(ISAuditTrail(
                id=uuid.uuid4(),
                session_id=uuid.UUID(entry.session_id) if entry.session_id else None,
                action=entry.action,
                entity_type=entry.entity_type,
                entity_id=uuid.UUID(entry.entity_id) if entry.entity_id else None,
                actor=entry.actor,
                details=entry.details,
                result=entry.result,
            ))
            await session.commit()
    except Exception as e:
        activity.logger.error("  ❌ Audit trail write failed: %s", e)

    return "ok"


async def log_audit(
    session_id: str,
    action: str,
    actor: str = "system",
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    result: Optional[str] = None,
) -> None:
    """
    Direct DB write for audit trail — used inside other activities
    (not dispatched as a separate Temporal activity).
    """
    from shared.database.db import AsyncSessionLocal
    from shared.models.is_models import ISAuditTrail

    try:
        async with AsyncSessionLocal() as session:
            session.add(ISAuditTrail(
                id=uuid.uuid4(),
                session_id=uuid.UUID(session_id) if session_id else None,
                action=action,
                entity_type=entity_type,
                entity_id=uuid.UUID(entity_id) if entity_id else None,
                actor=actor,
                details=details,
                result=result,
            ))
            await session.commit()
    except Exception:
        pass  # Best-effort — never block the calling activity
