"""
Knowledge-base loaders for the Implementation Mapping Agent.

Centralises reading ERPNext KB JSON files so mapping/classification/extraction
can share cached, deterministic inputs.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List

from containers.knowledge_base.erpnext.schema.compose import (
    column_priors,
    compose_field_mappings,
    corpus_rules,
    doctype_mapping,
    filename_priors,
    merge_policies,
)

_KB_DIR = Path(__file__).resolve().parent.parent.parent / "knowledge_base" / "erpnext"
_GRAPH_PATH = _KB_DIR / "erpnext_doctype_graph.json"
_BASELINE_PATH = _KB_DIR / "erpnext_deafaults_baseline.json"


@lru_cache(maxsize=1)
def field_mappings() -> Dict[str, Any]:
    return compose_field_mappings()


@lru_cache(maxsize=1)
def doctype_graph() -> Dict[str, Any]:
    try:
        with open(_GRAPH_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


@lru_cache(maxsize=1)
def baseline_defaults() -> Dict[str, Any]:
    try:
        with open(_BASELINE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


__all__ = [
    "field_mappings",
    "doctype_graph",
    "baseline_defaults",
    "corpus_rules",
    "merge_policies",
    "filename_priors",
    "column_priors",
    "doctype_mapping",
]
