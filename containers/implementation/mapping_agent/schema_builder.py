"""
Dynamic Pydantic schema builder for ERPNext doctypes.

Source of truth:
- containers/knowledge_base/erpnext/schema/field_mappings.json
Optional enrichment:
- containers/knowledge_base/erpnext/erpnext_doctype_graph.json (for missing child_fields)

This schema is used to force LLM extraction to conform to required fields,
date formats, numeric types, and child table structure.
"""

from __future__ import annotations

import re
from datetime import date
from functools import lru_cache
from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel, ConfigDict, Field, create_model
from typing import Literal

from containers.implementation.mapping_agent.kb import doctype_graph, field_mappings

# Lazy import to avoid circular dep; only used as async fallback
_live_schema_mod = None

def _get_live_schema_mod():
    global _live_schema_mod
    if _live_schema_mod is None:
        try:
            from containers.implementation.mapping_agent import live_schema as _ls
            _live_schema_mod = _ls
        except Exception:
            pass
    return _live_schema_mod


def _literal_from_options(options: Any):
    if isinstance(options, list) and options and all(isinstance(x, str) for x in options):
        # Guard against huge enums
        if len(options) <= 50:
            return Literal.__getitem__(tuple(options))
    if isinstance(options, str) and "\n" in options:
        opts = [o.strip() for o in options.split("\n") if o.strip()]
        if opts and len(opts) <= 50:
            return Literal.__getitem__(tuple(opts))
    return None


def _type_for_field(fieldtype: str, cfg: Dict[str, Any]):
    ft = str(fieldtype or "").strip().lower()
    if ft == "date":
        return date
    if ft in ("float", "currency", "percent"):
        return float
    if ft in ("int", "integer"):
        return int
    if ft in ("check", "boolean"):
        return bool
    if ft == "select":
        lit = _literal_from_options(cfg.get("options"))
        return lit or str
    # Link / Dynamic Link / Data / Text
    return str


def _parse_child_fields_from_graph(doctype: str, table_fieldname: str) -> List[str]:
    """
    Graph required_fields sometimes include strings like:
      'items (item_code, qty, rate)'
    We parse those to build a minimal child schema when KB lacks child_fields.
    """
    g = doctype_graph() or {}
    req = (
        g.get("doctypes", {})
         .get(doctype, {})
         .get("required_fields", [])
    ) or []
    out: List[str] = []
    for r in req:
        s = str(r)
        m = re.match(rf"^{re.escape(table_fieldname)}\s*\((.*?)\)\s*$", s, flags=re.IGNORECASE)
        if not m:
            continue
        inner = m.group(1)
        parts = [p.strip() for p in inner.split(",") if p.strip()]
        out.extend(parts)
    # De-dupe while preserving order
    seen = set()
    final = []
    for x in out:
        if x not in seen:
            seen.add(x)
            final.append(x)
    return final


def _fallback_child_type(child_field: str):
    k = str(child_field or "").lower()
    if any(tok in k for tok in ("qty", "quantity", "rate", "amount", "price", "total")):
        return float
    return str


def _build_child_model(doctype: str, table_fieldname: str, table_cfg: Dict[str, Any]) -> Type[BaseModel]:
    child_fields_cfg = table_cfg.get("child_fields") or {}

    fields: Dict[str, tuple[Any, Any]] = {}
    required: set[str] = set()

    if child_fields_cfg:
        for _, cfg in child_fields_cfg.items():
            fname = cfg.get("fieldname") or ""
            if not fname:
                continue
            ftype = _type_for_field(cfg.get("fieldtype"), cfg)
            is_req = bool(cfg.get("mandatory"))
            if is_req:
                required.add(fname)
                fields[fname] = (ftype, ...)
            else:
                fields[fname] = (Optional[ftype], None)
    else:
        # Graph-driven fallback: infer minimal child keys
        inferred = _parse_child_fields_from_graph(doctype, table_fieldname)
        for f in inferred:
            t = _fallback_child_type(f)
            fields[f] = (t, ...)

    if not fields:
        # Last-resort: allow any object if we cannot infer anything
        fields["name"] = (Optional[str], None)

    model = create_model(  # type: ignore[misc]
        f"{doctype}_{table_fieldname}_Row",
        __config__=ConfigDict(extra="ignore"),
        **fields,
    )
    return model


@lru_cache(maxsize=128)
def build_doctype_record_model(doctype: str) -> Type[BaseModel]:
    """Build a Pydantic model from the static KB (field_mappings.json).

    Uses @lru_cache because the KB is static — the model is the same for all
    projects. If the doctype is not in the KB, the model will have only
    `name: Optional[str]` and `_kb_miss = True` on the model's __doc__ to
    signal that a live fallback should be attempted.
    """
    kb = field_mappings() or {}
    dt_cfg = (kb.get("doctypes") or {}).get(doctype) or {}
    fmap = dt_cfg.get("field_mappings") or {}

    mandatory_fields = set(dt_cfg.get("mandatory_fields") or [])
    fields: Dict[str, tuple[Any, Any]] = {}
    table_fields: Dict[str, Dict[str, Any]] = {}

    # Merge graph required_fields into schema to prevent Pydantic stripping system fields
    g = doctype_graph() or {}
    graph_required_raw = (g.get("doctypes", {}).get(doctype, {}).get("required_fields", [])) or []
    graph_system_fields = set()
    for field_spec in graph_required_raw:
        # Parse "naming_series" or "items (item_code, qty)" → extract field name
        field_name = str(field_spec).split("(")[0].strip()
        if field_name and field_name not in fmap:
            # System field in graph but not in KB field_mappings
            graph_system_fields.add(field_name)

    # First pass: classify table vs scalar fields
    for _, cfg in fmap.items():
        fname = cfg.get("fieldname") or ""
        if not fname:
            continue
        if "[]" in fname:
            continue
        if str(cfg.get("fieldtype") or "").strip().lower() == "table":
            table_fields[fname] = cfg
        else:
            ftype = _type_for_field(cfg.get("fieldtype"), cfg)
            is_req = bool(cfg.get("mandatory")) or (fname in mandatory_fields)
            if is_req:
                fields[fname] = (ftype, ...)
            else:
                fields[fname] = (Optional[ftype], None)
    
    # Add graph system fields as optional to preserve them through Pydantic validation
    for sys_field in graph_system_fields:
        if sys_field not in fields:
            fields[sys_field] = (Optional[str], None)

    # Second pass: add child tables
    for table_fname, table_cfg in table_fields.items():
        child_model = _build_child_model(doctype, table_fname, table_cfg)
        min_rows = table_cfg.get("minimum_rows")
        if min_rows and isinstance(min_rows, int) and min_rows > 0:
            fields[table_fname] = (List[child_model], Field(default_factory=list, min_length=min_rows))
        else:
            fields[table_fname] = (List[child_model], Field(default_factory=list))

    # KB miss — minimal fallback. Callers should use build_extraction_wrapper_model_live()
    # which will attempt a live schema fetch from the project's ERP instance.
    if not fields:
        fields["name"] = (Optional[str], None)

    model = create_model(  # type: ignore[misc]
        f"{doctype}_Record",
        __config__=ConfigDict(extra="ignore"),
        **fields,
    )
    return model


def _is_kb_miss(doctype: str) -> bool:
    """True when the KB has no field_mappings entry for this doctype."""
    kb = field_mappings() or {}
    dt_cfg = (kb.get("doctypes") or {}).get(doctype) or {}
    return not bool(dt_cfg.get("field_mappings"))


@lru_cache(maxsize=128)
def build_extraction_wrapper_model(doctype: str) -> Type[BaseModel]:
    """Build the extraction wrapper from static KB only (fast, cached)."""
    record_model = build_doctype_record_model(doctype)
    wrapper = create_model(  # type: ignore[misc]
        f"{doctype}_ExtractionResult",
        __config__=ConfigDict(extra="ignore"),
        records=(List[record_model], Field(default_factory=list)),
    )
    return wrapper


async def build_extraction_wrapper_model_live(
    doctype: str,
    project_id: Optional[str] = None,
) -> Type[BaseModel]:
    """
    Build the extraction wrapper, with a live ERP schema fallback for KB-miss doctypes.

    This is the async version used by extract_unstructured_records() and
    validate_records_against_schema() during Temporal activity execution.

    - If the doctype is in the KB → identical to build_extraction_wrapper_model() (fast).
    - If the doctype is missing from KB AND project_id is provided → fetches schema
      live from Project.deployment_details ERP instance via ERP-agnostic adapter.
    - If live fetch also fails → falls back to minimal {"name": str} model (logs warning).
    """
    import logging as _logging
    _log = _logging.getLogger(__name__)

    # KB-hit: use the fast cached path
    if not _is_kb_miss(doctype):
        return build_extraction_wrapper_model(doctype)

    # KB-miss: attempt live fetch using project's deployment_details credentials
    ls_mod = _get_live_schema_mod()
    if ls_mod is None or not project_id:
        _log.warning(
            "schema_builder: KB miss for %s and no live fallback available "
            "(live_schema module=%s, project_id=%s) — using minimal model",
            doctype, ls_mod is not None, project_id,
        )
        return build_extraction_wrapper_model(doctype)  # returns minimal model

    live_fields = await ls_mod.fetch_live_doctype_schema(doctype, project_id)

    if not live_fields:
        _log.warning(
            "schema_builder: live fetch returned no fields for %s (project=%s) "
            "— falling back to minimal KB model",
            doctype, project_id,
        )
        return build_extraction_wrapper_model(doctype)

    _log.info(
        "schema_builder: KB miss for %s — live ERP schema (%d fields) via project=%s",
        doctype, len(live_fields), project_id,
    )

    # Build field dict from live schema
    fields: Dict[str, tuple[Any, Any]] = {}
    for f in live_fields:
        fname = (f.get("fieldname") or "").strip()
        if not fname or str(f.get("fieldtype") or "").strip().lower() == "table":
            continue
        ftype = _type_for_field(f.get("fieldtype") or "Data", f)
        if bool(f.get("mandatory")):
            fields[fname] = (ftype, ...)
        else:
            fields[fname] = (Optional[ftype], None)

    if not fields:
        fields["name"] = (Optional[str], None)

    # Build a non-cached model (name includes project_id slice to avoid collision)
    record_model = create_model(  # type: ignore[misc]
        f"{doctype}_Live_Record",
        __config__=ConfigDict(extra="ignore"),
        **fields,
    )
    wrapper = create_model(  # type: ignore[misc]
        f"{doctype}_Live_ExtractionResult",
        __config__=ConfigDict(extra="ignore"),
        records=(List[record_model], Field(default_factory=list)),
    )
    return wrapper
