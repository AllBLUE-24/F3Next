"""Archetype registry — single KB→code bridge for Discovery scoping and LLM hints."""

from __future__ import annotations

import json
import logging
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

_DISCOVERY_KB = Path(__file__).resolve().parent / "kb"
_CATALOG_PATH = _DISCOVERY_KB / "archetype_catalog.json"
_F3ICHE_DIR = Path(__file__).resolve().parent.parent / "knowledge_base" / "common" / "f3iches"
_GRAPH_PATH = (
    Path(__file__).resolve().parent.parent
    / "knowledge_base"
    / "erpnext"
    / "erpnext_doctype_graph.json"
)

_SIGNAL_MIN_SCORE = 1


@lru_cache(maxsize=1)
def _load_doctype_graph_keys() -> frozenset[str]:
    if not _GRAPH_PATH.is_file():
        return frozenset()
    try:
        with open(_GRAPH_PATH, encoding="utf-8") as f:
            graph = json.load(f)
        return frozenset((graph.get("doctypes") or {}).keys())
    except Exception as e:
        logger.warning("Failed to load doctype graph for archetype registry: %s", e)
        return frozenset()


@lru_cache(maxsize=1)
def load_catalog() -> dict[str, Any]:
    """Load global archetype catalog."""
    if not _CATALOG_PATH.is_file():
        return {"archetypes": [], "_source": "missing"}
    try:
        with open(_CATALOG_PATH, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and isinstance(data.get("archetypes"), list):
            return data
    except Exception as e:
        logger.warning("Failed to load archetype catalog: %s", e)
    return {"archetypes": [], "_source": "error"}


def load_f3iche_archetypes(f3iche_id: Optional[str]) -> list[dict[str, Any]]:
    """Load bottlenecks[] from a F3iche JSON."""
    if not f3iche_id:
        return []
    path = _F3ICHE_DIR / f"{f3iche_id}.json"
    if not path.is_file():
        return []
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        raw = data.get("bottlenecks")
        if not isinstance(raw, list):
            return []
        return [b for b in raw if isinstance(b, dict) and b.get("archetype_id")]
    except Exception as e:
        logger.debug("No bottlenecks[] for %s: %s", f3iche_id, e)
        return []


def merged_archetypes(f3iche_id: Optional[str] = None) -> list[dict[str, Any]]:
    """
    F3iche bottlenecks override catalog entries with the same archetype_id.
    Order: f3iche entries first, then catalog-only entries.
    """
    by_id: dict[str, dict[str, Any]] = {}
    for entry in load_catalog().get("archetypes") or []:
        aid = str(entry.get("archetype_id") or "").strip()
        if aid:
            by_id[aid] = dict(entry)
    for entry in load_f3iche_archetypes(f3iche_id):
        aid = str(entry.get("archetype_id") or "").strip()
        if aid:
            by_id[aid] = dict(entry)
    return list(by_id.values())


def list_archetype_ids(f3iche_id: Optional[str] = None) -> list[str]:
    return sorted(
        str(a.get("archetype_id") or "").strip()
        for a in merged_archetypes(f3iche_id)
        if a.get("archetype_id")
    )


def get_by_id(archetype_id: Optional[str], f3iche_id: Optional[str] = None) -> Optional[dict[str, Any]]:
    """Return archetype dict for id, or None."""
    aid = str(archetype_id or "").strip()
    if not aid:
        return None
    for entry in merged_archetypes(f3iche_id):
        if str(entry.get("archetype_id") or "").strip() == aid:
            return entry
    return None


def _signal_score(text: str, signals: list[str]) -> int:
    if not text or not signals:
        return 0
    haystack = text.lower()
    score = 0
    for signal in signals:
        sig = str(signal or "").strip().lower()
        if not sig:
            continue
        if sig in haystack:
            score += 1
            continue
        if len(sig) > 4 and re.search(re.escape(sig), haystack, re.I):
            score += 1
    return score


def match_by_signals(
    text: str,
    f3iche_id: Optional[str] = None,
    *,
    min_score: int = _SIGNAL_MIN_SCORE,
    top_k: int = 1,
) -> list[tuple[dict[str, Any], int]]:
    """
    Score archetypes by signal hits in text.
    Returns [(archetype, score), ...] sorted by score desc.
    """
    if not text.strip():
        return []
    ranked: list[tuple[dict[str, Any], int]] = []
    for entry in merged_archetypes(f3iche_id):
        signals = entry.get("signals") or []
        score = _signal_score(text, signals)
        if score >= min_score:
            ranked.append((entry, score))
    ranked.sort(key=lambda x: (-x[1], str(x[0].get("archetype_id") or "")))
    return ranked[:top_k]


def best_signal_match(
    text: str,
    f3iche_id: Optional[str] = None,
    *,
    min_score: int = _SIGNAL_MIN_SCORE,
) -> Optional[tuple[dict[str, Any], int]]:
    matches = match_by_signals(text, f3iche_id, min_score=min_score, top_k=1)
    return matches[0] if matches else None


def canonicalize_seed(name: str) -> str:
    raw = str(name or "").strip()
    if not raw:
        return ""
    return raw.split(" (")[0].strip()


def resolve_seed_doctypes(
    archetype: dict[str, Any],
    template_seeds: list[str],
    *,
    allow_graph_extension: bool = True,
) -> tuple[list[str], list[str]]:
    """
    Resolve day1_seed_hints against template and optional graph.

    Returns (resolved_seeds, graph_extensions) where graph_extensions are hints
    included via erpnext_doctype_graph but not in template_seeds.
    """
    template_set = set(template_seeds)
    graph_keys = _load_doctype_graph_keys() if allow_graph_extension else frozenset()

    resolved: list[str] = []
    graph_extensions: list[str] = []

    for hint in archetype.get("day1_seed_hints") or []:
        dt = canonicalize_seed(str(hint))
        if not dt:
            continue
        if dt in template_set:
            if dt not in resolved:
                resolved.append(dt)
        elif allow_graph_extension and dt in graph_keys:
            if dt not in resolved:
                resolved.append(dt)
                graph_extensions.append(dt)
        else:
            logger.debug(
                "Archetype %s hint %s not in template or graph",
                archetype.get("archetype_id"),
                dt,
            )

    defer = {
        canonicalize_seed(str(d))
        for d in (archetype.get("defer_typically") or [])
        if d
    }
    resolved = [d for d in resolved if d not in defer]
    return resolved, graph_extensions


def validate_archetype_load(f3iche_id: Optional[str] = None) -> list[str]:
    """Return warning strings for archetypes missing day1_seed_hints."""
    warnings: list[str] = []
    for entry in merged_archetypes(f3iche_id):
        aid = entry.get("archetype_id")
        if not entry.get("day1_seed_hints"):
            warnings.append(f"archetype {aid!r} has no day1_seed_hints")
    return warnings
