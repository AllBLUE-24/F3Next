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


@router.post("/{f3iche_id}/invalidate-cache", summary="Invalidate F3iche cache")
async def invalidate_f3iche_cache(
    f3iche_id: str,
    x_f3_admin_key: Optional[str] = Header(default=None, alias="X-F3-Admin-Key"),
):
    """
    Invalidate Context Engine L1/L2 cache for a specific F3iche.
    
    Use this endpoint when:
    - You've updated F3iche JSON files directly on disk
    - You want to force agents to reload F3iche definitions
    - You've made changes outside the upsert endpoint
    
    Example:
        curl -X POST http://localhost:8000/admin/f3iches/manufacturing_project_chemical/invalidate-cache \
             -H "X-F3-Admin-Key: your-admin-key"
    """
    _require_admin(x_f3_admin_key)

    from shared.context_engine import get_context_engine

    try:
        await get_context_engine().invalidate_f3iche(f3iche_id)
        logger.info("F3iche cache invalidated: %s", f3iche_id)
    except Exception as e:
        logger.error("F3iche cache invalidation failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Cache invalidation failed: {str(e)}")

    # Also publish to Redis for distributed cache invalidation
    try:
        rurl = os.getenv("REDIS_URL", "").strip()
        if rurl:
            import redis.asyncio as redis_async

            async with redis_async.from_url(rurl, decode_responses=True) as r:
                await r.publish("f3iche_updates", f3iche_id)
                logger.info("F3iche update published to Redis: %s", f3iche_id)
    except Exception as e:
        logger.debug("Redis publish skipped: %s", e)

    return {
        "ok": True,
        "f3iche_id": f3iche_id,
        "action": "cache_invalidated",
        "message": f"Context Engine cache cleared for F3iche '{f3iche_id}'",
    }


@router.post("/invalidate-all", summary="Invalidate all F3iche caches")
async def invalidate_all_f3iche_caches(
    x_f3_admin_key: Optional[str] = Header(default=None, alias="X-F3-Admin-Key"),
):
    """
    Invalidate Context Engine L1/L2 cache for ALL F3iches.
    
    Use this when:
    - You've updated multiple F3iche JSON files in bulk
    - You want to force a complete cache refresh across the system
    
    Example:
        curl -X POST http://localhost:8000/admin/f3iches/invalidate-all \
             -H "X-F3-Admin-Key: your-admin-key"
    """
    _require_admin(x_f3_admin_key)

    from sqlalchemy import select

    from shared.context_engine import get_context_engine
    from shared.database.db import AsyncSessionLocal
    from shared.models.f3iche_models import F3icheDefinition

    # Get all F3iche IDs from database
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(F3icheDefinition.f3iche_id).distinct()
        )
        f3iche_ids = [row[0] for row in res.fetchall()]

    invalidated = []
    failed = []

    engine = get_context_engine()
    for f3iche_id in f3iche_ids:
        try:
            await engine.invalidate_f3iche(f3iche_id)
            invalidated.append(f3iche_id)
            logger.info("F3iche cache invalidated: %s", f3iche_id)
        except Exception as e:
            failed.append({"f3iche_id": f3iche_id, "error": str(e)})
            logger.error("F3iche cache invalidation failed for %s: %s", f3iche_id, e)

    # Publish bulk invalidation event to Redis
    try:
        rurl = os.getenv("REDIS_URL", "").strip()
        if rurl:
            import redis.asyncio as redis_async

            async with redis_async.from_url(rurl, decode_responses=True) as r:
                await r.publish("f3iche_updates", "*")  # Wildcard for "all"
                logger.info("Bulk F3iche invalidation published to Redis")
    except Exception as e:
        logger.debug("Redis publish skipped: %s", e)

    return {
        "ok": len(failed) == 0,
        "invalidated": len(invalidated),
        "failed": len(failed),
        "f3iche_ids": invalidated,
        "errors": failed,
        "message": f"Invalidated {len(invalidated)} F3iche(s), {len(failed)} failed",
    }
