"""Load bottleneck archetype hints for the recommend LLM (Research-owned content)."""

from __future__ import annotations

import json
import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

from containers.discovery.archetype_registry import (
    get_by_id,
    load_catalog,
    merged_archetypes,
    signal_match_rankings,
)

logger = logging.getLogger(__name__)

_KB_COMMON = Path(__file__).resolve().parent.parent / "knowledge_base" / "common"
_MVP_MAP_PATH = _KB_COMMON / "mvp_bottleneck_map.json"

USE_F3ICHE_BOTTLENECKS = os.getenv("DISCOVERY_USE_F3ICHE_BOTTLENECKS", "true").lower() in (
    "1",
    "true",
    "yes",
)
USE_MVP_MAP_FALLBACK = os.getenv("DISCOVERY_USE_MVP_MAP_FALLBACK", "false").lower() in (
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
    """Research-maintained catalog. Legacy mvp_bottleneck_map.json only if flag enabled."""
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

    logger.warning(
        "Using deprecated mvp_bottleneck_map.json — set DISCOVERY_USE_MVP_MAP_FALLBACK=false "
        "and expand archetype_catalog.json instead"
    )
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
    return {"archetypes": archetypes, "_source": "mvp_bottleneck_map.json (deprecated)"}


def _format_archetype_line(a: dict[str, Any]) -> list[str]:
    lines: list[str] = []
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
    defer = a.get("defer_typically") or []
    if defer:
        lines.append(f"  defer_typically: {', '.join(defer)}")
    note = str(a.get("notes") or "").strip()
    if note:
        lines.append(f"  notes: {note}")
    return lines


def _format_archetypes_for_prompt(archetypes: list[dict[str, Any]], *, header: str) -> str:
    if not archetypes:
        return "(none — infer from coverage pain_point)"
    lines = [header]
    for a in archetypes:
        lines.extend(_format_archetype_line(a))
    return "\n".join(lines)


def _format_merged_archetypes_for_prompt(
    f3iche_id: Optional[str],
    *,
    catalog: dict[str, Any],
) -> str:
    """Merged F3iche overrides + global catalog; optional sector grouping from _meta.sectors."""
    merged = merged_archetypes(f3iche_id if USE_F3ICHE_BOTTLENECKS else None)
    if not merged:
        legacy = load_global_archetype_catalog()
        merged = legacy.get("archetypes") or []
        source = legacy.get("_source", "unknown")
    else:
        source = "archetype_registry (F3iche overrides + global catalog)"

    if not merged:
        return "(none — infer mvp_focus from coverage pain_point and industry)"

    sectors: dict[str, list[str]] = (catalog.get("_meta") or {}).get("sectors") or {}
    if not sectors:
        header = f"ARCHETYPE HINTS (source: {source}"
        if f3iche_id and USE_F3ICHE_BOTTLENECKS:
            header += f", niche: {f3iche_id}"
        header += "):"
        return _format_archetypes_for_prompt(merged, header=header)

    by_id = {str(a.get("archetype_id")): a for a in merged if a.get("archetype_id")}
    grouped_ids: set[str] = set()
    parts = [f"ARCHETYPE HINTS BY SECTOR (source: {source}):"]

    for sector_name, ids in sectors.items():
        sector_entries = [by_id[i] for i in ids if i in by_id]
        if not sector_entries:
            continue
        grouped_ids.update(str(a.get("archetype_id")) for a in sector_entries)
        parts.append(_format_archetypes_for_prompt(sector_entries, header=f"\n[{sector_name}]"))

    ungrouped = [a for aid, a in by_id.items() if aid not in grouped_ids]
    if ungrouped:
        parts.append(_format_archetypes_for_prompt(ungrouped, header="\n[Other / cross-sector]"))

    return "\n".join(parts)


def _format_ranked_archetypes(
    rankings: list[dict[str, Any]],
    f3iche_id: Optional[str],
) -> str:
    """Top signal-ranked archetypes for planner context (not full catalog dump)."""
    entries: list[dict[str, Any]] = []
    for rank in rankings:
        entry = get_by_id(rank.get("archetype_id"), f3iche_id)
        if entry:
            entries.append({**entry, "_signal_score": rank.get("score", 0)})
    if not entries:
        return ""
    header = (
        f"TOP MATCHED REFERENCE PATTERNS (signal-ranked from transcript, "
        f"top {len(entries)}):"
    )
    lines = [header]
    for a in entries:
        score = a.get("_signal_score", 0)
        lines.append(f"\n[score={score}]")
        lines.extend(_format_archetype_line(a))
    return "\n".join(lines)


async def build_bottleneck_hint_context(
    primary_bottleneck: str,
    *,
    f3iche_id: Optional[str] = None,
    transcript: Optional[str] = None,
    top_k: int = 3,
) -> str:
    """
    Context block for planner / recommendation prompts.

    When transcript is provided, returns signal-ranked top-k archetypes instead of
    dumping the entire catalog (reduces noise, improves pattern matching).
    """
    parts: list[str] = []
    catalog = load_catalog()

    retrieval_text = " ".join(
        t for t in (transcript or "", primary_bottleneck or "") if t
    ).strip()
    if retrieval_text:
        rankings = signal_match_rankings(retrieval_text, f3iche_id, top_k=top_k)
        ranked_block = _format_ranked_archetypes(rankings, f3iche_id)
        if ranked_block:
            parts.append(ranked_block)

    if not parts:
        merged_block = _format_merged_archetypes_for_prompt(f3iche_id, catalog=catalog)
        if merged_block and not merged_block.startswith("(none"):
            parts.append(merged_block)

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
