"""Load Tier 1 (files), Tier 2 (DB + bundled JSON), Tier 3 (pgvector snippets)."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional

from sqlalchemy import select, text

from shared.context_engine.config import ERPNEXT_KB, F3ICHE_DIR
from shared.context_engine.versioning import json_checksum

logger = logging.getLogger(__name__)


def _load_json(path: Path) -> dict[str, Any]:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning("Tier1: failed to load %s: %s", path, e)
        return {}


def merge_patch(target: Any, patch: Any) -> Any:
    """RFC 7396 JSON Merge Patch (dicts only; sufficient for our graphs)."""
    if not isinstance(patch, dict):
        return patch
    if not isinstance(target, dict):
        target = {}
    out = dict(target)
    for k, v in patch.items():
        if v is None:
            out.pop(k, None)
        elif isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = merge_patch(out[k], v)
        else:
            out[k] = v
    return out


class Tier1Loader:
    """Core graph + field maps + validation rules."""

    def __init__(self) -> None:
        self._bundle: Optional[dict[str, Any]] = None
        self._checksum = ""

    def load(self) -> tuple[dict[str, Any], str]:
        if self._bundle is not None:
            return self._bundle, self._checksum

        graph_path = ERPNEXT_KB / "erpnext_doctype_graph.json"
        fm_path = ERPNEXT_KB / "schema" / "field_mappings.json"
        vr_path = ERPNEXT_KB / "schema" / "validation_rules.json"

        graph = _load_json(graph_path)
        field_mappings = _load_json(fm_path)
        validation_rules = _load_json(vr_path)

        self._bundle = {
            "doctype_graph": graph,
            "field_mappings": field_mappings,
            "validation_rules": validation_rules,
        }
        self._checksum = json_checksum(self._bundle)
        return self._bundle, self._checksum


async def load_tier2_f3iche(f3iche_id: str) -> dict[str, Any]:
    """
    Prefer DB row (custom/bundled migrated), else bundled JSON file.
    """
    if not f3iche_id:
        return {}

    try:
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
            if row and row.definition:
                return dict(row.definition) if isinstance(row.definition, dict) else {}
    except Exception as e:
        logger.debug("Tier2 DB load skipped or failed: %s", e)

    path = F3ICHE_DIR / f"{f3iche_id}.json"
    if path.is_file():
        return _load_json(path)
    return {}


def apply_f3iche_to_graph(tier1_graph_doc: dict[str, Any], f3iche: dict[str, Any]) -> dict[str, Any]:
    """Apply f3iche overrides.tier1_extensions onto doctypes map."""
    base = dict(tier1_graph_doc)
    doctypes = dict(base.get("doctypes") or {})
    overrides = (f3iche.get("overrides") or {}).get("tier1_extensions") or {}
    if isinstance(overrides, dict):
        for dt, patch in overrides.items():
            if isinstance(patch, dict):
                cur = doctypes.get(dt, {})
                doctypes[dt] = merge_patch(cur, patch)
    base["doctypes"] = doctypes
    return base


async def retrieve_kb_chunks(
    query_embedding_str: str,
    top_k: int = 5,
    kb_source_prefix: Optional[str] = None,
) -> list[str]:
    """Vector similarity search against kb_embeddings."""
    from shared.database.db import AsyncSessionLocal, engine

    if "sqlite" in str(engine.url):
        return []

    stmt = text("""
        SELECT content
        FROM kb_embeddings
        ORDER BY embedding <=> CAST(:vector AS vector)
        LIMIT :lim
    """)
    params: dict[str, Any] = {"vector": query_embedding_str, "lim": top_k}
    if kb_source_prefix:
        stmt = text("""
            SELECT content
            FROM kb_embeddings
            WHERE kb_source LIKE :pfx
            ORDER BY embedding <=> CAST(:vector AS vector)
            LIMIT :lim
        """)
        params["pfx"] = f"{kb_source_prefix}%"

    out: list[str] = []
    try:
        async with AsyncSessionLocal() as session:
            res = await session.execute(stmt, params)
            for row in res:
                out.append(row[0])
            if not out and kb_source_prefix:
                res2 = await session.execute(
                    text("""
                        SELECT content
                        FROM kb_embeddings
                        ORDER BY embedding <=> CAST(:vector AS vector)
                        LIMIT :lim
                    """),
                    {"vector": query_embedding_str, "lim": top_k},
                )
                for row in res2:
                    out.append(row[0])
    except Exception as e:
        logger.warning("Tier3 vector search failed: %s", e)
    return out
