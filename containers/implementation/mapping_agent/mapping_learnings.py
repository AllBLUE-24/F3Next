"""Session-scoped column→field learnings from successful mappings (P2)."""
from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional, Set

# Methods that produced a novel column mapping worth reusing in-session.
_LEARNING_METHODS = frozenset({
    "llm_column_map",
    "llm_inferred",
    "kb_fuzzy",
    "fuzzy_match",
})


def collect_successful_learnings(
    *,
    doctype: str,
    source_file: str,
    field_mapping: Dict[str, str],
    methods: Dict[str, str],
) -> List[Dict[str, Any]]:
    """Extract reusable column→field pairs from a successful map pass."""
    out: List[Dict[str, Any]] = []
    for src_col, erp_field in (field_mapping or {}).items():
        if not src_col or not erp_field:
            continue
        method = str((methods or {}).get(src_col) or "kb_local")
        if method == "kb_local":
            continue
        if method not in _LEARNING_METHODS and not method.startswith("llm"):
            continue
        out.append({
            "doctype": doctype,
            "source_column": str(src_col),
            "erp_field": str(erp_field),
            "source_file": source_file,
            "method": method,
            "kb_action": (
                f"Promote '{src_col}' → {erp_field} in mapping/{doctype}.json user_input_synonyms"
            ),
        })
    return out


def merge_learnings(
    existing: List[Dict[str, Any]],
    new_items: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Dedupe by (doctype, source_column, erp_field)."""
    seen: Set[tuple[str, str, str]] = set()
    merged: List[Dict[str, Any]] = []
    for item in list(existing or []) + list(new_items or []):
        if not isinstance(item, dict):
            continue
        key = (
            str(item.get("doctype") or ""),
            str(item.get("source_column") or ""),
            str(item.get("erp_field") or ""),
        )
        if not key[0] or not key[1] or not key[2] or key in seen:
            continue
        seen.add(key)
        merged.append(item)
    return merged


def apply_learnings_to_kb(
    kb: Dict[str, Any],
    doctype: str,
    learnings: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Runtime KB overlay — add session-learned synonyms without editing JSON files."""
    relevant = [
        l for l in (learnings or [])
        if str(l.get("doctype") or "") == doctype and l.get("source_column") and l.get("erp_field")
    ]
    if not relevant:
        return kb

    patched = copy.deepcopy(kb)
    dt_cfg = patched.setdefault("doctypes", {}).setdefault(doctype, {})
    fmap = dt_cfg.setdefault("field_mappings", {})

    for entry in relevant:
        erp_field = str(entry["erp_field"])
        src_col = str(entry["source_column"])
        child_suffix = None
        if "." in erp_field:
            table, child = erp_field.split(".", 1)
            cfg = fmap.get(table) or {"fieldname": table, "fieldtype": "Table", "child_fields": {}}
            child_fields = cfg.setdefault("child_fields", {})
            child_cfg = child_fields.get(child) or {"fieldname": child, "user_input_synonyms": []}
            syns = list(child_cfg.get("user_input_synonyms") or [])
            if src_col not in syns:
                syns.append(src_col)
            child_cfg["user_input_synonyms"] = syns
            child_fields[child] = child_cfg
            fmap[table] = cfg
            continue

        cfg = None
        for _fn, fc in fmap.items():
            if str(fc.get("fieldname") or _fn) == erp_field:
                cfg = fc
                break
        if cfg is None:
            cfg = fmap.setdefault(erp_field, {
                "fieldname": erp_field,
                "fieldtype": "Data",
                "user_input_synonyms": [],
            })
        syns = list(cfg.get("user_input_synonyms") or [])
        if src_col not in syns:
            syns.append(src_col)
        cfg["user_input_synonyms"] = syns

    return patched


def _learnings_r2_key(company_slug: str, project_id: str, session_id: str) -> str:
    return f"{company_slug}/{project_id}/mappings/session_learnings/{session_id}.json"


async def load_session_learnings(
    company_slug: str,
    project_id: str,
    session_id: str,
) -> List[Dict[str, Any]]:
    from shared.r2_client import r2_read_json

    key = _learnings_r2_key(company_slug, project_id, session_id)
    try:
        data = await r2_read_json(key, bucket="clean-data") or {}
        items = data.get("learnings") if isinstance(data, dict) else []
        return [i for i in (items or []) if isinstance(i, dict)]
    except Exception:
        return []


async def save_session_learnings(
    company_slug: str,
    project_id: str,
    session_id: str,
    learnings: List[Dict[str, Any]],
) -> str:
    from shared.r2_client import r2_write_json

    key = _learnings_r2_key(company_slug, project_id, session_id)
    payload = {
        "session_id": session_id,
        "project_id": project_id,
        "learnings": learnings,
        "count": len(learnings),
    }
    await r2_write_json(key, payload, bucket="clean-data")
    return key
