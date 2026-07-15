"""Resolve CVS snapshot payloads — Supabase row or R2 fallback."""

from __future__ import annotations

import logging
from typing import Any, Optional, Protocol

logger = logging.getLogger(__name__)

PAYLOAD_IN_R2_KEY = "_payload_in_r2"


class _SnapshotRow(Protocol):
    data: Any
    r2_key: Optional[str]


def is_payload_in_r2(data: dict | None) -> bool:
    return bool((data or {}).get(PAYLOAD_IN_R2_KEY))


def cvs_supabase_payload_stub(full_data: dict) -> dict:
    """
    Minimal metadata kept in Supabase when the full payload is stored in R2.

    Keeps counts for status endpoints without pulling multi-MB JSONB from Postgres.
    """
    counts = full_data.get("counts") if isinstance(full_data.get("counts"), dict) else {}
    return {
        PAYLOAD_IN_R2_KEY: True,
        "counts": counts,
    }


async def resolve_snapshot_data(row: _SnapshotRow | None) -> dict | None:
    """
    Return the full CVS layer payload for a ContextSnapshot row.

    Reads from row.data when the full payload is inline; otherwise loads from R2
    via row.r2_key when the row is a metadata stub.
    """
    if row is None:
        return None

    data = row.data or {}
    if data and not is_payload_in_r2(data):
        return data

    r2_key = getattr(row, "r2_key", None)
    if r2_key:
        try:
            from shared.r2_client import r2_read_json

            loaded = await r2_read_json(r2_key)
            if loaded:
                return loaded
        except Exception as e:
            logger.warning("CVS: R2 read failed for key=%s: %s", r2_key, e)

    if is_payload_in_r2(data):
        return None

    return data or None
