"""
KB-driven field semantics for ERP-OS payload building and validation.

Resolves clarity entity keys → ERP field specs using KB-04 mappings,
KB-07 doctype graph (name_field, setup layers), and os_validation.json.
No hardcoded doctype lists in callers.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

from containers.knowledge_base.erpnext.schema.compose import compose_field_mappings, doctype_mapping

_SCHEMA_DIR = Path(__file__).resolve().parent.parent / "containers" / "knowledge_base" / "erpnext"
_GRAPH_PATH = _SCHEMA_DIR / "erpnext_doctype_graph.json"
_OS_VALIDATION_PATH = _SCHEMA_DIR / "schema" / "shared" / "os_validation.json"

# Entity keys handled outside generic field mapping (child tables, etc.)
_NON_FIELD_ENTITY_KEYS = frozenset({
    "items", "amount", "currency", "payment_type", "party_type", "mode_of_payment",
    "stock_entry_type", "project", "from_warehouse", "to_warehouse", "limit",
    "from_date", "to_date", "document_name", "is_stock_item", "extra",
})


def _read_json(path: Path) -> dict[str, Any]:
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


@lru_cache(maxsize=1)
def _doctype_graph() -> dict[str, Any]:
    return _read_json(_GRAPH_PATH)


@lru_cache(maxsize=1)
def _os_validation_config() -> dict[str, Any]:
    return _read_json(_OS_VALIDATION_PATH)


def get_doctype_config(doctype: str) -> dict[str, Any]:
    cfg = doctype_mapping(doctype)
    return cfg if isinstance(cfg, dict) else {}


def get_field_mappings(doctype: str) -> dict[str, Any]:
    return get_doctype_config(doctype).get("field_mappings") or {}


def get_name_field(doctype: str) -> Optional[str]:
    dt = (_doctype_graph().get("doctypes") or {}).get(doctype) or {}
    name = dt.get("name_field")
    return str(name).strip() if name else None


def get_setup_layer_doctypes() -> frozenset[str]:
    """All doctypes listed in setup_layers (masters + config)."""
    layers = _doctype_graph().get("setup_layers") or {}
    names: set[str] = set()
    for layer_dts in layers.values():
        if isinstance(layer_dts, list):
            names.update(str(x) for x in layer_dts if x)
    return frozenset(names)


def is_master_create_doctype(doctype: str) -> bool:
    """True when doctype appears in KB-07 setup_layers (master/config records)."""
    return doctype in get_setup_layer_doctypes()


def resolve_entity_to_field(doctype: str, entity_key: str) -> Optional[tuple[str, dict[str, Any]]]:
    """
    Map a clarity entity key to (entity_key_in_kb, field_spec).
    Matches direct field_mappings keys or user_input_synonyms (case-insensitive).
    """
    key = str(entity_key or "").strip()
    if not key or key in _NON_FIELD_ENTITY_KEYS:
        return None

    fm = get_field_mappings(doctype)
    if not fm:
        return None

    if key in fm and isinstance(fm[key], dict):
        return key, fm[key]

    key_cf = key.casefold()
    for spec_key, spec in fm.items():
        if not isinstance(spec, dict):
            continue
        if spec_key.casefold() == key_cf:
            return spec_key, spec
        synonyms = spec.get("user_input_synonyms") or []
        if any(str(s).casefold() == key_cf for s in synonyms if s):
            return spec_key, spec

    return None


def field_spec_for_fieldname(doctype: str, fieldname: str) -> Optional[dict[str, Any]]:
    """Return KB field spec for an ERP fieldname on a doctype."""
    fn = str(fieldname or "").strip()
    if not fn:
        return None
    for spec in get_field_mappings(doctype).values():
        if isinstance(spec, dict) and str(spec.get("fieldname") or "") == fn:
            return spec
    return None


def is_link_field_spec(field_spec: dict[str, Any]) -> bool:
    return str(field_spec.get("fieldtype") or "") == "Link"


def link_target_doctype(field_spec: dict[str, Any]) -> Optional[str]:
    options = field_spec.get("options")
    if options and isinstance(options, str) and options.strip():
        return options.strip()
    return None


def cvs_registry_key_for_link(link_target: str) -> Optional[str]:
    mapping = _os_validation_config().get("link_target_to_cvs_registry") or {}
    return mapping.get(link_target)


def should_validate_link_in_cvs(
    action: str,
    target_doctype: str,
    field_spec: dict[str, Any],
) -> bool:
    """
    Validate Link field existence in CVS when referencing master data.
    Skip when creating the master record itself (name field or self-referential create).
    """
    if not is_link_field_spec(field_spec):
        return False

    if str(action or "").casefold() != "create":
        return True

    fieldname = str(field_spec.get("fieldname") or "")
    name_field = get_name_field(target_doctype)
    if name_field and fieldname == name_field:
        return False

    link_target = link_target_doctype(field_spec)
    if link_target and link_target == target_doctype:
        return False

    return True


def apply_kb_defaults_to_entities(doctype: str, entities: dict[str, Any]) -> dict[str, Any]:
    """Return entities with KB default_value applied for missing mandatory fields."""
    out = dict(entities)
    dt_cfg = get_doctype_config(doctype)
    fm = dt_cfg.get("field_mappings") or {}
    for field in dt_cfg.get("mandatory_fields") or []:
        if out.get(field) not in (None, "", [], {}):
            continue
        spec = fm.get(field) if isinstance(fm.get(field), dict) else {}
        default = spec.get("default_value")
        if default not in (None, ""):
            out[field] = default
    return out


def normalize_entities_for_doctype(doctype: str, entities: dict[str, Any]) -> dict[str, Any]:
    """Map clarity entity keys onto KB field keys via synonym resolution."""
    out = dict(entities)
    for entity_key, value in list(entities.items()):
        if value in (None, "", [], {}):
            continue
        resolved = resolve_entity_to_field(doctype, entity_key)
        if resolved:
            kb_key, _ = resolved
            if kb_key != entity_key and kb_key not in out:
                out[kb_key] = value
    return apply_kb_defaults_to_entities(doctype, out)


def tier1_mandatory_missing(
    doctype: str,
    entities: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return (missing_fields, applied_defaults) using modular KB layout."""
    entities = normalize_entities_for_doctype(doctype, entities)
    dt_cfg = get_doctype_config(doctype)
    fm = dt_cfg.get("field_mappings") or {}
    mandatory = dt_cfg.get("mandatory_fields") or []
    missing: list[dict[str, Any]] = []
    applied: list[dict[str, Any]] = []

    for field in mandatory:
        if entities.get(field) not in (None, "", [], {}):
            continue
        spec = fm.get(field) if isinstance(fm.get(field), dict) else {}
        default = spec.get("default_value")
        if default not in (None, ""):
            applied.append({"field": field, "value": default, "reason": "kb_default"})
            continue
        missing.append({
            "field": field,
            "tier": 1,
            "question": f"Please provide `{field}` for {doctype}.",
            "reasoning": "Tier1 schema: mandatory field missing.",
            "suggested_default": None,
            "apqc_reference": None,
            "erpnext_reference": None,
        })
    return missing, applied


def filter_missing_for_doctype(doctype: str, missing: list[Any]) -> list[dict[str, Any]]:
    """Drop LLM-suggested fields that do not apply to this doctype's KB schema."""
    fm = get_field_mappings(doctype)
    mandatory = set(get_doctype_config(doctype).get("mandatory_fields") or [])
    kept: list[dict[str, Any]] = []
    for entry in missing:
        if not isinstance(entry, dict):
            continue
        field = str(entry.get("field") or "")
        top = field.split(".", 1)[0]
        if top == "items" and top not in fm:
            if doctype not in _ITEMS_DOCTYPES():
                continue
        if top in fm or top in mandatory:
            kept.append(entry)
    return kept


@lru_cache(maxsize=1)
def _ITEMS_DOCTYPES() -> frozenset[str]:
    """Doctypes whose KB schema includes an items child table entity."""
    names: set[str] = set()
    raw = compose_field_mappings()
    for dt_name, cfg in (raw.get("doctypes") or {}).items():
        if isinstance(cfg, dict) and "items" in (cfg.get("field_mappings") or {}):
            names.add(str(dt_name))
    return frozenset(names)


def map_entities_to_payload_fields(
    doctype: str,
    entities: dict[str, Any],
) -> dict[str, Any]:
    """
    Map clarity entities → ERP payload keys using KB-04 only.
    Skips entity keys with no mapping for this doctype.
    """
    payload: dict[str, Any] = {}
    entities = normalize_entities_for_doctype(doctype, entities)

    for entity_key, value in entities.items():
        if value in (None, "", [], {}):
            continue
        if entity_key in _NON_FIELD_ENTITY_KEYS:
            continue
        resolved = resolve_entity_to_field(doctype, entity_key)
        if not resolved:
            continue
        _, spec = resolved
        fn = str(spec.get("fieldname") or entity_key)
        payload[fn] = value

    return payload


def apply_field_defaults_to_payload(doctype: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Fill payload fields from KB default_value when not already set."""
    for _key, spec in get_field_mappings(doctype).items():
        if not isinstance(spec, dict):
            continue
        fn = str(spec.get("fieldname") or _key)
        if fn in payload and payload[fn] not in (None, "", [], {}):
            continue
        default = spec.get("default_value")
        if default not in (None, ""):
            payload[fn] = default
    return payload


def clear_semantics_cache() -> None:
    """Clear cached KB reads (for tests)."""
    _doctype_graph.cache_clear()
    _os_validation_config.cache_clear()
    _ITEMS_DOCTYPES.cache_clear()
    doctype_mapping.cache_clear()
    compose_field_mappings.cache_clear()
