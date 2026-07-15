"""Unified Context Engine — 3-tier + CVS layers with tiered cache."""

from __future__ import annotations

import logging
import time
import uuid as uuid_lib
from typing import Any, Optional

from sqlalchemy import select

from shared.context_engine.cache import ContextCache
from shared.context_engine.loader import (
    Tier1Loader,
    apply_f3iche_to_graph,
    load_tier2_f3iche,
    retrieve_kb_chunks,
)
from shared.context_engine.metrics import CONTEXT_ENGINE_LATENCY, CONTEXT_ENGINE_REQUESTS, observe_cache_hit
from shared.context_engine.models import ProjectContext
from shared.context_engine.versioning import context_cache_key, tier2_cache_key

logger = logging.getLogger(__name__)

_tier1_loader = Tier1Loader()
_global_cache = ContextCache()


class ContextEngine:
    """Loads Tier1 + Tier2 + CVS; Tier3 on demand via retrieve_kb_chunks."""

    def __init__(self, cache: Optional[ContextCache] = None) -> None:
        self._cache = cache or _global_cache

    async def get_context(
        self,
        project_id: str,
        f3iche_id: str,
        layers: Optional[list[str]] = None,
        version: Optional[int] = None,
        include_tier3: bool = False,
    ) -> ProjectContext:
        if layers is None:
            layers = ["identity", "master_data"]

        key = context_cache_key(project_id, f3iche_id or "none", layers, version)
        t0 = time.perf_counter()

        cached = await self._cache.get(key)
        if cached is not None:
            observe_cache_hit("l1_or_l2")
            if CONTEXT_ENGINE_REQUESTS is not None:
                CONTEXT_ENGINE_REQUESTS.labels(result="cache_hit").inc()
            if CONTEXT_ENGINE_LATENCY is not None:
                CONTEXT_ENGINE_LATENCY.observe(time.perf_counter() - t0)
            return ProjectContext(**cached)

        tier1_bundle, checksum = _tier1_loader.load()
        graph_doc = tier1_bundle.get("doctype_graph") or {}

        t2_key = tier2_cache_key(f3iche_id or "none", None)
        t2_cached = await self._cache.get(t2_key)
        if isinstance(t2_cached, dict):
            tier2 = t2_cached
            observe_cache_hit("tier2_subcache")
        else:
            tier2 = await load_tier2_f3iche(f3iche_id or "")
            await self._cache.set(t2_key, tier2)

        merged_graph = apply_f3iche_to_graph(graph_doc, tier2)

        cvs_data: dict[str, Any] = {}
        try:
            from shared.cvs_snapshot_loader import resolve_snapshot_data
            from shared.database.db import AsyncSessionLocal
            from shared.models.cvs_models import ContextSnapshot
            from sqlalchemy import text

            try:
                pid_uuid: uuid_lib.UUID = uuid_lib.UUID(str(project_id))
            except ValueError:
                # Resolve slug -> UUID (projects.company_slug)
                async with AsyncSessionLocal() as session:
                    res = await session.execute(
                        text("SELECT id FROM projects WHERE company_slug = :slug LIMIT 1"),
                        {"slug": str(project_id)},
                    )
                    resolved = res.scalar()
                if not resolved:
                    raise ValueError(f"Unknown project identifier '{project_id}' (not UUID, not company_slug)")
                pid_uuid = uuid_lib.UUID(str(resolved))

            async with AsyncSessionLocal() as session:
                for layer in layers:
                    q = await session.execute(
                        select(ContextSnapshot)
                        .where(
                            ContextSnapshot.project_id == pid_uuid,
                            ContextSnapshot.layer == layer,
                        )
                        .order_by(ContextSnapshot.version.desc())
                        .limit(1)
                    )
                    row = q.scalars().first()
                    if row:
                        payload = await resolve_snapshot_data(row)
                        if payload:
                            cvs_data[layer] = payload
                        if version is not None and row.version != version:
                            pass  # pinned mismatch — still return latest row; caller may validate
        except Exception as e:
            logger.warning("ContextEngine: CVS load failed for %s: %s", project_id, e)

        payload = {
            "project_id": project_id,
            "f3iche_id": f3iche_id or "",
            "layers": list(layers),
            "tier1": tier1_bundle,
            "tier2_raw": tier2,
            "tier2_merged_graph": merged_graph,
            "cvs": cvs_data,
            "tier1_checksum": checksum,
            "context_version": version,
        }

        _ = include_tier3  # reserved for future Tier3 inline assembly
        pc = ProjectContext(
            project_id=project_id,
            f3iche_id=f3iche_id or "",
            layers=list(layers),
            tier1=tier1_bundle,
            tier2_raw=tier2,
            tier2_merged_graph=merged_graph,
            cvs=cvs_data,
            tier1_checksum=checksum,
            context_version=version,
        )
        await self._cache.set(key, payload)
        if CONTEXT_ENGINE_REQUESTS is not None:
            CONTEXT_ENGINE_REQUESTS.labels(result="miss").inc()
        if CONTEXT_ENGINE_LATENCY is not None:
            CONTEXT_ENGINE_LATENCY.observe(time.perf_counter() - t0)
        return pc

    async def get_tier3_chunks(
        self,
        query_embedding_str: str,
        top_k: int = 5,
        kb_source_prefix: Optional[str] = None,
    ) -> list[str]:
        return await retrieve_kb_chunks(query_embedding_str, top_k, kb_source_prefix)

    async def invalidate_project(self, project_id: str) -> None:
        await self._cache.invalidate_prefix(f"ctx:v1:{project_id}:")

    async def invalidate_f3iche(self, f3iche_id: str) -> None:
        await self._cache.invalidate_prefix(f"tier2:v1:{f3iche_id}:")


_engine: Optional[ContextEngine] = None


def get_context_engine() -> ContextEngine:
    global _engine
    if _engine is None:
        _engine = ContextEngine()
    return _engine
