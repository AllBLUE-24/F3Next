"""Machine-readable import field policy from F3iche KB files."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

_F3ICHE_DIR = (
    Path(__file__).resolve().parent.parent.parent
    / "knowledge_base" / "common" / "f3iches"
)


@lru_cache(maxsize=16)
def load_f3iche(f3iche_id: str) -> Dict[str, Any]:
    if not f3iche_id:
        return {}
    path = _F3ICHE_DIR / f"{f3iche_id}.json"
    if not path.is_file():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def import_field_policy(f3iche_id: str) -> Dict[str, Any]:
    return load_f3iche(f3iche_id).get("import_field_policy") or {}


def default_when_missing(f3iche_id: str) -> Dict[str, Any]:
    policy = import_field_policy(f3iche_id)
    raw = policy.get("default_when_missing") or {}
    return dict(raw) if isinstance(raw, dict) else {}


def always_ask_doctypes(f3iche_id: str) -> Set[str]:
    policy = import_field_policy(f3iche_id)
    items = policy.get("always_ask") or []
    return {str(x).strip() for x in items if str(x).strip()}


def defer_until_post_mvp(f3iche_id: str) -> Set[str]:
    policy = import_field_policy(f3iche_id)
    items = policy.get("defer_until_post_mvp") or []
    return {str(x).strip() for x in items if str(x).strip()}


def f3iche_default_for(doctype: str, field: str, f3iche_id: str) -> Optional[Any]:
    key = f"{doctype}.{field}"
    return default_when_missing(f3iche_id).get(key)


def is_deferred_doctype(doctype: str, f3iche_id: str) -> bool:
    return doctype in defer_until_post_mvp(f3iche_id)


def must_ask_for_doctype(doctype: str, f3iche_id: str) -> bool:
    return doctype in always_ask_doctypes(f3iche_id)
