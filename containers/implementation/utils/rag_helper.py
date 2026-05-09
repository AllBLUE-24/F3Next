"""
containers/implementation/utils/rag_helper.py
=============================================
Shared RAG retrieval helper for all IS activities.

Mirrors the OS `business_analyzer._rag_retrieve` pattern exactly:
  - Embeds query text via shared.embedding_generator (OpenAI)
  - Searches kb_embeddings via shared.context_engine.loader.retrieve_kb_chunks
  - Caches results in Redis via shared.rag_cache

Usage:
    from containers.implementation.utils.rag_helper import rag_retrieve

    apqc_chunks  = await rag_retrieve("chemical manufacturing compliance", "apqc_pcf",   top_k=6)
    erp_chunks   = await rag_retrieve("BOM ERPNext setup",                 "erpnext_docs", top_k=5)
    f3iche_chunks = await rag_retrieve("chemical process workflows",        "f3iche_manufacturing_project_chemical", top_k=6)
"""
from __future__ import annotations

import hashlib
import logging
from typing import List

logger = logging.getLogger(__name__)


def _hash_query(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


async def rag_retrieve(
    query_text: str,
    kb_source_prefix: str,
    top_k: int = 6,
) -> List[str]:
    """
    Embed `query_text`, search kb_embeddings filtered by `kb_source_prefix`,
    and return the top-k content strings.

    Results are cached in Redis (keyed by prefix + query hash + k) so repeated
    calls within the same Temporal activity execution are free.

    Falls back to empty list on any error — never raises.
    """
    cache_key = f"is_rag:{kb_source_prefix}:{_hash_query(query_text)}:k{top_k}"

    # ── 1. Cache check ────────────────────────────────────────────────────────
    try:
        from shared.rag_cache import cache_get_json, cache_set_json
        cached = await cache_get_json(cache_key)
        if isinstance(cached, list) and cached:
            logger.debug("[rag_retrieve] cache hit | prefix=%s k=%d", kb_source_prefix, top_k)
            return [str(x) for x in cached]
    except Exception:
        pass  # Redis unavailable — proceed to live query

    # ── 2. Embed ──────────────────────────────────────────────────────────────
    try:
        from shared.embedding_generator import generate_embedding, embedding_to_pgvector_str
        vec = await generate_embedding(query_text)
        vec_str = embedding_to_pgvector_str(vec)
    except Exception as e:
        logger.warning("[rag_retrieve] embedding failed for prefix=%s: %s", kb_source_prefix, e)
        return []

    # ── 3. pgvector search ────────────────────────────────────────────────────
    try:
        from shared.context_engine.loader import retrieve_kb_chunks
        chunks = await retrieve_kb_chunks(vec_str, top_k=top_k, kb_source_prefix=kb_source_prefix)
    except Exception as e:
        logger.warning("[rag_retrieve] vector search failed for prefix=%s: %s", kb_source_prefix, e)
        return []

    logger.info(
        "[rag_retrieve] prefix=%-35s top_k=%d → %d chunks returned",
        kb_source_prefix, top_k, len(chunks),
    )

    # ── 4. Cache result ───────────────────────────────────────────────────────
    try:
        from shared.rag_cache import cache_set_json
        await cache_set_json(cache_key, chunks)
    except Exception:
        pass

    return chunks
