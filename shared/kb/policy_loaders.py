"""
Load canonical KB policy JSON for IS and OS (branch 04 policy spine).
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

_KB_ERPNEXT = (
    Path(__file__).resolve().parent.parent.parent
    / "containers"
    / "knowledge_base"
    / "erpnext"
    / "schema"
)
_SHARED = _KB_ERPNEXT / "shared"


def _read_json(path: Path) -> dict[str, Any]:
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


@lru_cache(maxsize=1)
def get_os_validation_config() -> dict[str, Any]:
    return _read_json(_SHARED / "os_validation.json")


@lru_cache(maxsize=1)
def get_validation_rules_kb() -> dict[str, Any]:
    return _read_json(_KB_ERPNEXT / "validation_rules.json")


@lru_cache(maxsize=1)
def get_is_import_rules() -> dict[str, Any]:
    """IS validate step: required fields, enums, link messages."""
    kb = get_validation_rules_kb()
    return kb.get("is_import_rules") or {}


@lru_cache(maxsize=1)
def get_execution_preflight_rules() -> list[dict[str, Any]]:
    raw = _read_json(_SHARED / "execution_preflight_rules.json")
    rules = raw.get("rules") or []
    return [r for r in rules if isinstance(r, dict)]


@lru_cache(maxsize=1)
def get_link_resolution_policy() -> dict[str, Any]:
    return _read_json(_SHARED / "link_resolution_policy.json")


def clear_policy_caches() -> None:
    """Test helper."""
    get_os_validation_config.cache_clear()
    get_validation_rules_kb.cache_clear()
    get_is_import_rules.cache_clear()
    get_execution_preflight_rules.cache_clear()
    get_link_resolution_policy.cache_clear()
