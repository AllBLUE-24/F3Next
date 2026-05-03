"""
Admin API for Tier 2 F3iche definitions (hot-reload).

Secured with optional `X-F3-Admin-Key` when `ADMIN_F3ICHE_KEY` is set.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Literal, Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/f3iches", tags=["Admin — F3iches"])


class F3icheUpsertBody(BaseModel):
    f3iche_id: str = Field(..., min_length=1, max_length=128)
    definition: dict[str, Any]
    source: Literal["bundled", "custom"] = "custom"


def _require_admin(x_f3_admin_key: Optional[str]) -> None:
    expected = os.getenv("ADMIN_F3ICHE_KEY", "").strip()
    if not expected:
        return
    if (x_f3_admin_key or "").strip() != expected:
        raise HTTPException(status_code=403, detail="Invalid or missing admin key")


@router.post("", summary="Create or update a F3iche definition")
async def upsert_f3iche(
    body: F3icheUpsertBody,
    x_f3_admin_key: Optional[str] = Header(default=None, alias="X-F3-Admin-Key"),
):
    _require_admin(x_f3_admin_key)

    from sqlalchemy import select

    from shared.context_engine import get_context_engine
    from shared.database.db import AsyncSessionLocal
    from shared.models.f3iche_models import F3icheDefinition

    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(F3icheDefinition).where(F3icheDefinition.f3iche_id == body.f3iche_id)
        )
        row = res.scalars().first()
        if row:
            row.version = int(row.version or 0) + 1
            row.definition = body.definition
            row.source = body.source
        else:
            session.add(
                F3icheDefinition(
                    f3iche_id=body.f3iche_id,
                    version=1,
                    source=body.source,
                    definition=body.definition,
                )
            )
        await session.commit()

    try:
        await get_context_engine().invalidate_f3iche(body.f3iche_id)
    except Exception as e:
        logger.warning("F3iche cache invalidate: %s", e)

    try:
        rurl = os.getenv("REDIS_URL", "").strip()
        if rurl:
            import redis.asyncio as redis_async

            async with redis_async.from_url(rurl, decode_responses=True) as r:
                await r.publish("f3iche_updates", body.f3iche_id)
    except Exception as e:
        logger.debug("Redis publish skipped: %s", e)

    return {"ok": True, "f3iche_id": body.f3iche_id}


@router.get("/{f3iche_id}", summary="Get latest F3iche definition")
async def get_f3iche(
    f3iche_id: str,
    x_f3_admin_key: Optional[str] = Header(default=None, alias="X-F3-Admin-Key"),
):
    _require_admin(x_f3_admin_key)

    from sqlalchemy import select

    from shared.database.db import AsyncSessionLocal
    from shared.models.f3iche_models import F3icheDefinition

    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(F3icheDefinition)
            .where(F3icheDefinition.f3iche_id == f3iche_id)
            .order_by(F3icheDefinition.version.desc())
            .limit(1)
        )
        row = res.scalars().first()

    if not row:
        raise HTTPException(status_code=404, detail="F3iche not found in database")

    return {
        "f3iche_id": row.f3iche_id,
        "version": row.version,
        "source": row.source,
        "definition": row.definition,
    }
