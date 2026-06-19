"""SchemaResolver v1 — bridge KB gaps with live ERP schema or safe heuristics."""
from __future__ import annotations

import copy
import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

_DEFAULT_ITEMS_CHILD = {
    "item_code": {
        "fieldname": "item_code",
        "fieldtype": "Link",
        "options": "Item",
        "mandatory": True,
        "user_input_synonyms": ["product", "item", "sku", "material"],
    },
    "qty": {
        "fieldname": "qty",
        "fieldtype": "Float",
        "mandatory": True,
        "user_input_synonyms": ["quantity", "units", "ordered_qty", "vol"],
    },
    "rate": {
        "fieldname": "rate",
        "fieldtype": "Currency",
        "mandatory": False,
        "user_input_synonyms": ["price", "unit_price", "rate"],
    },
}


def _items_table_cfg(doctype: str, kb: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    dt_cfg = (kb.get("doctypes") or {}).get(doctype) or {}
    fmap = dt_cfg.get("field_mappings") or {}
    items = fmap.get("items") or {}
    if str(items.get("fieldtype") or "").lower() == "table":
        return items
    return None


def kb_missing_child_fields(doctype: str, kb: Dict[str, Any]) -> List[str]:
    """Return table fieldnames that lack child_fields definitions."""
    dt_cfg = (kb.get("doctypes") or {}).get(doctype) or {}
    missing: List[str] = []
    for _fn, cfg in (dt_cfg.get("field_mappings") or {}).items():
        if str(cfg.get("fieldtype") or "").lower() != "table":
            continue
        if not cfg.get("child_fields"):
            missing.append(str(cfg.get("fieldname") or _fn))
    return missing


def _heuristic_child_fields(table_name: str) -> Dict[str, Any]:
    if table_name == "items":
        return copy.deepcopy(_DEFAULT_ITEMS_CHILD)
    return {}


def resolve_kb_gaps_sync(
    doctype: str,
    kb: Dict[str, Any],
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Patch KB copy with heuristic child_fields when modular mapping is incomplete.

    Returns (patched_kb, resolver_meta) for logging / KB promotion checklist.
    """
    missing = kb_missing_child_fields(doctype, kb)
    if not missing:
        return kb, {"resolved": False, "doctype": doctype}

    patched = copy.deepcopy(kb)
    dt_cfg = patched.setdefault("doctypes", {}).setdefault(doctype, {})
    fmap = dt_cfg.setdefault("field_mappings", {})
    promotions: List[Dict[str, Any]] = []

    for table_name in missing:
        cfg = fmap.get(table_name) or {}
        if cfg.get("child_fields"):
            continue
        child_fields = _heuristic_child_fields(table_name)
        if not child_fields:
            continue
        cfg = dict(cfg)
        cfg["child_fields"] = child_fields
        fmap[table_name] = cfg
        promotions.append({
            "doctype": doctype,
            "table": table_name,
            "action": "inject_heuristic_child_fields",
            "fields": list(child_fields.keys()),
        })
        logger.info(
            "schema_resolver: injected heuristic child_fields for %s.%s",
            doctype,
            table_name,
        )

    meta = {
        "resolved": bool(promotions),
        "doctype": doctype,
        "missing_tables": missing,
        "promotions": promotions,
        "source": "heuristic",
    }
    return patched, meta


def merge_live_schema_into_kb(
    doctype: str,
    kb: Dict[str, Any],
    live_fields: List[Dict[str, Any]],
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Build a minimal doctype entry from live ERP schema when KB module is missing."""
    if not live_fields:
        return kb, {"live_merged": False, "doctype": doctype}

    patched = copy.deepcopy(kb)
    fmap: Dict[str, Any] = {}
    mandatory: List[str] = []
    for f in live_fields:
        if not isinstance(f, dict):
            continue
        fname = str(f.get("fieldname") or "").strip()
        if not fname:
            continue
        syns = list(f.get("user_input_synonyms") or [fname])
        if fname not in syns:
            syns.insert(0, fname)
        entry = {
            "fieldname": fname,
            "fieldtype": f.get("fieldtype") or "Data",
            "mandatory": bool(f.get("mandatory") or f.get("reqd")),
            "options": f.get("options"),
            "user_input_synonyms": syns,
        }
        fmap[fname] = entry
        if entry["mandatory"]:
            mandatory.append(fname)

    patched.setdefault("doctypes", {})[doctype] = {
        "field_mappings": fmap,
        "mandatory_fields": mandatory,
        "_schema_source": "live_erp",
    }
    return patched, {
        "live_merged": True,
        "doctype": doctype,
        "field_count": len(fmap),
        "source": "live_schema",
    }


async def resolve_kb_gaps_async(
    doctype: str,
    kb: Dict[str, Any],
    *,
    project_id: Optional[str] = None,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Patch KB with heuristics and, when needed, live ERP schema for KB-miss doctypes.
    """
    patched, meta = resolve_kb_gaps_sync(doctype, kb)
    dt_in_kb = doctype in (patched.get("doctypes") or {})

    if not project_id:
        return patched, meta

    try:
        from containers.implementation.mapping_agent.live_schema import fetch_live_doctype_schema

        if not dt_in_kb:
            live_fields = await fetch_live_doctype_schema(doctype, project_id)
            if live_fields:
                patched, live_meta = merge_live_schema_into_kb(doctype, patched, live_fields)
                meta = {**meta, **live_meta, "resolved": True}
                logger.info(
                    "schema_resolver: merged live schema for KB-miss doctype %s (%d fields)",
                    doctype,
                    live_meta.get("field_count", 0),
                )
                return patched, meta

        live_fields = await fetch_live_doctype_schema(doctype, project_id)
        if live_fields:
            meta["live_field_count"] = len(live_fields)
            meta["live_schema_available"] = True
            logger.info(
                "schema_resolver: live schema available for %s (%d fields) — promote to KB",
                doctype,
                len(live_fields),
            )
    except Exception as e:
        logger.debug("schema_resolver: live fetch skipped for %s: %s", doctype, e)

    return patched, meta
