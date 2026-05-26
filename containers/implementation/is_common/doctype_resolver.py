"""
Canonical ERPNext doctype name resolution.

Normalizes annotated names (e.g. 'Stock Entry (Issue, Transfer, Manufacture)')
and resolves aliases from KB classifier hints and graph keys.
"""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Any, Dict, Iterable, List, Optional, Set

_PAREN_SUFFIX = re.compile(r"\s*\([^)]*\)\s*$")


def normalize_doctype_name(name: str) -> str:
    """Lowercase key for alias lookup; strip trailing parenthetical annotations."""
    s = str(name or "").strip()
    s = _PAREN_SUFFIX.sub("", s).strip()
    return re.sub(r"\s+", " ", s).lower()


def strip_annotations(name: str) -> str:
    """Display/canonical form: strip parenthetical suffix only."""
    s = str(name or "").strip()
    return _PAREN_SUFFIX.sub("", s).strip()


@lru_cache(maxsize=1)
def _alias_map() -> Dict[str, str]:
    from containers.knowledge_base.erpnext.schema.compose import compose_field_mappings

    alias: Dict[str, str] = {}

    def register(raw: str, canonical: str) -> None:
        key = normalize_doctype_name(raw)
        canon = strip_annotations(canonical)
        if key and canon and key not in alias:
            alias[key] = canon

    try:
        from containers.implementation.mapping_agent.kb import doctype_graph

        graph = doctype_graph() or {}
        for dt_name in (graph.get("doctypes") or {}).keys():
            register(dt_name, dt_name)
    except Exception:
        pass

    kb = compose_field_mappings() or {}
    for dt_name, dt_cfg in (kb.get("doctypes") or {}).items():
        canonical = strip_annotations(dt_cfg.get("doctype_name") or dt_name)
        register(dt_name, canonical)
        register(canonical, canonical)
        for hint in dt_cfg.get("doctype_classifier_hints") or []:
            register(hint, canonical)

    return alias


def resolve_doctype(name: str, *, fallback: bool = True) -> str:
    """Resolve to canonical doctype name."""
    raw = str(name or "").strip()
    if not raw:
        return raw
    stripped = strip_annotations(raw)
    key = normalize_doctype_name(raw)
    resolved = _alias_map().get(key)
    if resolved:
        return resolved
    return stripped if fallback else raw


def resolve_in_set(name: str, candidates: Iterable[str]) -> Optional[str]:
    """Find the candidate that matches name after normalization."""
    target = normalize_doctype_name(name)
    if not target:
        return None
    for c in candidates:
        if normalize_doctype_name(c) == target:
            return c
    resolved = resolve_doctype(name)
    for c in candidates:
        if normalize_doctype_name(c) == normalize_doctype_name(resolved):
            return c
    return None


def build_normalized_index(items: Dict[str, Any]) -> Dict[str, str]:
    """Map normalized doctype name → first key in items dict."""
    out: Dict[str, str] = {}
    for key in items:
        norm = normalize_doctype_name(key)
        if norm not in out:
            out[norm] = key
        resolved = normalize_doctype_name(resolve_doctype(key))
        if resolved not in out:
            out[resolved] = key
    return out


def lookup_normalized(items: Dict[str, Any], doctype: str) -> Optional[Any]:
    """Dict lookup tolerant of annotation / alias differences."""
    if doctype in items:
        return items[doctype]
    resolved = resolve_doctype(doctype)
    if resolved in items:
        return items[resolved]
    idx = build_normalized_index(items)
    key = idx.get(normalize_doctype_name(doctype)) or idx.get(normalize_doctype_name(resolved))
    if key is not None:
        return items.get(key)
    return None


def contains_doctype(items: Iterable[str], doctype: str) -> bool:
    target = normalize_doctype_name(resolve_doctype(doctype))
    return any(normalize_doctype_name(resolve_doctype(x)) == target for x in items)


def unique_canonical(names: Iterable[str]) -> List[str]:
    seen: Set[str] = set()
    out: List[str] = []
    for n in names:
        c = resolve_doctype(n)
        k = normalize_doctype_name(c)
        if k and k not in seen:
            seen.add(k)
            out.append(c)
    return out
