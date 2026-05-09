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
from typing import Any, Dict, List, Optional, Tuple, Type

from pydantic import BaseModel, ConfigDict, Field, create_model
from typing import Literal

from containers.implementation.mapping_agent.kb import doctype_graph, field_mappings


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

    fields: Dict[str, Tuple[Any, Any]] = {}
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
        __config__=ConfigDict(extra="forbid"),
        **fields,
    )
    return model


@lru_cache(maxsize=128)
def build_doctype_record_model(doctype: str) -> Type[BaseModel]:
    kb = field_mappings() or {}
    dt_cfg = (kb.get("doctypes") or {}).get(doctype) or {}
    fmap = dt_cfg.get("field_mappings") or {}

    mandatory_fields = set(dt_cfg.get("mandatory_fields") or [])
    fields: Dict[str, Tuple[Any, Any]] = {}
    table_fields: Dict[str, Dict[str, Any]] = {}

    # First pass: classify table vs scalar fields
    for _, cfg in fmap.items():
        fname = cfg.get("fieldname") or ""
        if not fname:
            continue
        if "[]" in fname:
            # Skip pseudo-path entries like "items[].sales_order"
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

    # Second pass: add child tables
    for table_fname, table_cfg in table_fields.items():
        child_model = _build_child_model(doctype, table_fname, table_cfg)
        min_rows = table_cfg.get("minimum_rows")
        if min_rows and isinstance(min_rows, int) and min_rows > 0:
            fields[table_fname] = (List[child_model], Field(default_factory=list, min_length=min_rows))
        else:
            fields[table_fname] = (List[child_model], Field(default_factory=list))

    # As a safety, if KB doesn't include any fields, accept a minimal dict.
    if not fields:
        fields["name"] = (Optional[str], None)

    model = create_model(  # type: ignore[misc]
        f"{doctype}_Record",
        __config__=ConfigDict(extra="forbid"),
        **fields,
    )
    return model


@lru_cache(maxsize=128)
def build_extraction_wrapper_model(doctype: str) -> Type[BaseModel]:
    record_model = build_doctype_record_model(doctype)
    wrapper = create_model(  # type: ignore[misc]
        f"{doctype}_ExtractionResult",
        __config__=ConfigDict(extra="forbid"),
        records=(List[record_model], Field(default_factory=list)),
    )
    return wrapper

