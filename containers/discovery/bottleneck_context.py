"""Load bottleneck archetype hints for the recommend LLM (Research-owned content)."""

from __future__ import annotations

import json
import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

from containers.discovery.archetype_registry import load_catalog, load_f3iche_archetypes

logger = logging.getLogger(__name__)

_KB_COMMON = Path(__file__).resolve().parent.parent / "knowledge_base" / "common"
_MVP_MAP_PATH = _KB_COMMON / "mvp_bottleneck_map.json"

USE_F3ICHE_BOTTLENECKS = os.getenv("DISCOVERY_USE_F3ICHE_BOTTLENECKS", "true").lower() in (
    "1",
    "true",
    "yes",
)
USE_MVP_MAP_FALLBACK = os.getenv("DISCOVERY_USE_MVP_MAP_FALLBACK", "true").lower() in (
    "1",
    "true",
    "yes",
)
USE_BOTTLENECK_RAG = os.getenv("DISCOVERY_USE_BOTTLENECK_RAG", "false").lower() in (
    "1",
    "true",
    "yes",
)


@lru_cache(maxsize=1)
def load_global_archetype_catalog() -> dict[str, Any]:
    """Research-maintained catalog (optional). Falls back to mvp_bottleneck_map.json."""
    data = load_catalog()
    if isinstance(data, dict) and data.get("archetypes"):
        return {**data, "_source": "containers/discovery/kb/archetype_catalog.json"}

    if not USE_MVP_MAP_FALLBACK or not _MVP_MAP_PATH.is_file():
        return {"archetypes": [], "_source": "none"}

    try:
        with open(_MVP_MAP_PATH, encoding="utf-8") as f:
            raw = json.load(f)
    except Exception as e:
        logger.warning("Failed to load mvp_bottleneck_map.json: %s", e)
        return {"archetypes": [], "_source": "none"}

    archetypes = []
    for key, entry in raw.items():
        if key.startswith("_") or not isinstance(entry, dict):
            continue
        archetypes.append(
            {
                "archetype_id": key,
                "primary_bottleneck": entry.get("primary_bottleneck", ""),
                "functional_requirements": entry.get("functional_requirements", []),
                "day1_seed_hints": entry.get("suggested_seed_doctypes", []),
            }
        )
    return {"archetypes": archetypes, "_source": "mvp_bottleneck_map.json"}


def load_f3iche_bottlenecks(f3iche_id: Optional[str]) -> list[dict[str, Any]]:
    """Read bottlenecks[] from a F3iche JSON once Research fills them in."""
    if not f3iche_id or not USE_F3ICHE_BOTTLENECKS:
        return []
    return load_f3iche_archetypes(f3iche_id)


def _format_archetypes_for_prompt(archetypes: list[dict[str, Any]], *, header: str) -> str:
    if not archetypes:
        return "(none — infer from coverage pain_point)"
    lines = [header]
    for a in archetypes:
        aid = a.get("archetype_id", "")
        lines.append(f"- {aid}: {a.get('primary_bottleneck', '')}")
        reqs = a.get("functional_requirements") or []
        if reqs:
            lines.append(f"  functional_requirements: {', '.join(reqs)}")
        seeds = a.get("day1_seed_hints") or a.get("suggested_seed_doctypes") or []
        if seeds:
            lines.append(f"  day1_seed_hints: {', '.join(seeds)}")
        signals = a.get("signals") or []
        if signals:
            lines.append(f"  signals: {', '.join(signals)}")
    return "\n".join(lines)


async def build_bottleneck_hint_context(
    primary_bottleneck: str,
    *,
    f3iche_id: Optional[str] = None,
) -> str:
    """
    Context block injected into RECOMMENDATION_PROMPT.
    Priority: F3iche bottlenecks[] → archetype_catalog → mvp map → optional RAG.
    """
    parts: list[str] = []

    f3iche_archetypes = load_f3iche_bottlenecks(f3iche_id)
    if f3iche_archetypes:
        parts.append(
            _format_archetypes_for_prompt(
                f3iche_archetypes,
                header=f"F3ICHE BOTTLENECKS ({f3iche_id or 'unknown'}):",
            )
        )

    catalog = load_global_archetype_catalog()
    global_archetypes = catalog.get("archetypes") or []
    if global_archetypes and not f3iche_archetypes:
        parts.append(
            _format_archetypes_for_prompt(
                global_archetypes,
                header=f"GLOBAL ARCHETYPE CATALOG (source: {catalog.get('_source', 'unknown')}):",
            )
        )

    if primary_bottleneck and USE_BOTTLENECK_RAG:
        try:
            from containers.implementation.utils.rag_helper import rag_retrieve

            chunks = await rag_retrieve(primary_bottleneck, "business_bottlenecks", top_k=2)
            if chunks:
                parts.append("RAG BOTTLENECK SNIPPETS:\n" + "\n\n".join(chunks))
        except Exception as e:
            logger.debug("Bottleneck RAG skipped: %s", e)

    if not parts:
        return "(none — infer mvp_focus from coverage pain_point and industry)"

    return "\n\n".join(parts)
