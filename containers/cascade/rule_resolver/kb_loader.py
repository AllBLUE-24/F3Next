"""Load cascade routing rules from KB JSON."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

_KB_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "knowledge_base"
    / "common"
    / "cascade_rules.json"
)


@lru_cache(maxsize=1)
def load_cascade_rules() -> dict[str, Any]:
    with _KB_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)


def match_rules(doctype: str, trigger_event: str) -> list[dict[str, Any]]:
    """Return KB rules matching doctype + Frappe webhook event."""
    kb = load_cascade_rules()
    rules = kb.get("rules") or []
    return [
        r
        for r in rules
        if r.get("doctype") == doctype and r.get("trigger_event") == trigger_event
    ]
