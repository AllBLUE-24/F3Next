"""
Compose the legacy field_mappings.json shape from modular KB files.

Modular layout (schema/):
  index.json
  corpus/          — party split rules, merge policies
  classification/  — global hints, filename priors
  mapping/         — one JSON file per ERPNext doctype
  shared/          — date/currency/quantity/default parsing rules
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

_SCHEMA_DIR = Path(__file__).resolve().parent
_LEGACY_PATH = _SCHEMA_DIR / "field_mappings.json"


def _read_json(path: Path) -> Dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _load_mapping_doctypes() -> Dict[str, Any]:
    mapping_dir = _SCHEMA_DIR / "mapping"
    if not mapping_dir.is_dir():
        return {}
    doctypes: Dict[str, Any] = {}
    for path in sorted(mapping_dir.glob("*.json")):
        cfg = _read_json(path)
        if not cfg:
            continue
        dt_name = str(cfg.get("doctype_name") or path.stem.replace("_", " "))
        doctypes[dt_name] = cfg
    return doctypes


@lru_cache(maxsize=1)
def compose_field_mappings() -> Dict[str, Any]:
    """Merge modular KB files into the monolithic field_mappings.json shape."""
    index = _read_json(_SCHEMA_DIR / "index.json")
    if not index:
        return _read_json(_LEGACY_PATH)

    party = _read_json(_SCHEMA_DIR / "corpus" / "party_entity_rules.json")
    global_hints = _read_json(_SCHEMA_DIR / "classification" / "global_hints.json")
    shared = _read_json(_SCHEMA_DIR / "shared" / "parsing_defaults.json")
    doctypes = _load_mapping_doctypes()

    composed: Dict[str, Any] = {
        "knowledge_base_id": index.get("knowledge_base_id", "field_mapping_rules"),
        "version": index.get("version", "2.0"),
        "erp_system": index.get("erp_system", "erpnext"),
        "last_updated": index.get("last_updated", ""),
        "description": index.get("description", ""),
        "party_type_synonyms": party.get("party_type_synonyms", {}),
        "doctype_keyword_hints": global_hints.get("doctype_keyword_hints", {}),
        "doctypes": doctypes,
    }
    for key in (
        "date_parsing_rules",
        "currency_parsing_rules",
        "quantity_parsing_rules",
        "default_value_rules",
    ):
        if key in shared:
            composed[key] = shared[key]

    return composed


@lru_cache(maxsize=1)
def corpus_rules() -> Dict[str, Any]:
    return _read_json(_SCHEMA_DIR / "corpus" / "party_entity_rules.json")


@lru_cache(maxsize=1)
def merge_policies() -> Dict[str, Any]:
    return _read_json(_SCHEMA_DIR / "corpus" / "merge_policies.json")


@lru_cache(maxsize=1)
def filename_priors() -> List[Dict[str, Any]]:
    data = _read_json(_SCHEMA_DIR / "classification" / "filename_priors.json")
    priors = data.get("priors") or []
    return priors if isinstance(priors, list) else []


@lru_cache(maxsize=1)
def column_priors() -> List[Dict[str, Any]]:
    data = _read_json(_SCHEMA_DIR / "classification" / "column_priors.json")
    priors = data.get("priors") or []
    return priors if isinstance(priors, list) else []


@lru_cache(maxsize=1)
def doctype_mapping(doctype: str) -> Dict[str, Any]:
    safe = doctype.replace("/", "_")
    path = _SCHEMA_DIR / "mapping" / f"{safe}.json"
    if path.is_file():
        return _read_json(path)
    return ((compose_field_mappings().get("doctypes") or {}).get(doctype) or {})


def clear_cache() -> None:
    compose_field_mappings.cache_clear()
    corpus_rules.cache_clear()
    merge_policies.cache_clear()
    filename_priors.cache_clear()
    column_priors.cache_clear()
    doctype_mapping.cache_clear()
