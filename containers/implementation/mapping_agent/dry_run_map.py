"""Deterministic dry-run mapping (Step 9 pipeline without R2 persist)."""
from __future__ import annotations

import csv
import io
import os
from typing import Any, Callable, Dict, List, Optional

from containers.implementation.is_common.party_rules import (
    find_split_column,
    is_customer_role,
    is_supplier_role,
)
from containers.implementation.mapping_agent.activities import _MappingEngine
from containers.implementation.mapping_agent.column_map_tiered import kb_fuzzy_map_columns
from containers.implementation.mapping_agent.defaults import (
    apply_defaults_and_normalize,
    fold_child_tables,
)
from containers.implementation.mapping_agent.preflight_fields import preflight_mapped_records


def _parse_rows(content: str) -> List[Dict[str, Any]]:
    rows = list(csv.DictReader(io.StringIO(content)))
    return [{k: v for k, v in r.items() if k is not None} for r in rows]


def _filter_party_rows(
    rows: List[Dict[str, Any]],
    columns: List[str],
    doctype: str,
) -> List[Dict[str, Any]]:
    role_col = find_split_column(columns)
    if not role_col:
        return rows
    if doctype == "Customer":
        return [r for r in rows if is_customer_role(r.get(role_col, ""))]
    if doctype == "Supplier":
        return [r for r in rows if is_supplier_role(r.get(role_col, ""))]
    return rows


def _map_columns_deterministic(
    engine: _MappingEngine,
    columns: List[str],
    doctype: str,
    kb: Dict[str, Any],
    *,
    sample_row: Optional[Dict[str, Any]] = None,
) -> Dict[str, str]:
    tier1 = engine.map_columns(columns, doctype, sample_row=sample_row)
    return kb_fuzzy_map_columns(columns, doctype, kb, already_mapped=tier1)


def _apply_field_mapping(
    rows: List[Dict[str, Any]],
    field_mapping: Dict[str, str],
) -> List[Dict[str, Any]]:
    mapped: List[Dict[str, Any]] = []
    for row in rows:
        mapped_row: Dict[str, Any] = {}
        for src_col, val in row.items():
            if src_col in field_mapping:
                mapped_row[field_mapping[src_col]] = val
        mapped.append(mapped_row)
    return mapped


def dry_run_map_file(
    content: str,
    doctype: str,
    *,
    kb: Dict[str, Any],
    row_filter: Optional[Callable[[List[Dict[str, Any]], List[str]], List[Dict[str, Any]]]] = None,
    company_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Run map → fold → defaults → preflight without persisting.

    Uses Tier 1 KB exact + Tier 3 KB fuzzy only (no LLM unless IS_DRY_RUN_LLM=1).
    """
    rows = _parse_rows(content)
    if not rows:
        return {
            "passed": False,
            "field_mapping": {},
            "preflight": {"blocking": True, "missing_fields": [], "messages": ["No rows in file"]},
            "record_count": 0,
            "methods": {},
        }

    columns = [c for c in rows[0].keys() if c]
    if row_filter:
        rows = row_filter(rows, columns)
    elif doctype in ("Customer", "Supplier"):
        rows = _filter_party_rows(rows, columns, doctype)

    if not rows:
        return {
            "passed": False,
            "field_mapping": {},
            "preflight": {
                "blocking": True,
                "missing_fields": [],
                "messages": [f"No rows matched party filter for {doctype}"],
            },
            "record_count": 0,
            "methods": {},
        }

    engine = _MappingEngine()
    engine._field_mappings = kb
    field_mapping = _map_columns_deterministic(
        engine, columns, doctype, kb, sample_row=rows[0],
    )
    methods = {src: "kb_local" for src in field_mapping}

    mapped = _apply_field_mapping(rows, field_mapping)
    folded = fold_child_tables(doctype, mapped)
    normalized = apply_defaults_and_normalize(
        doctype, folded, context=company_context or {},
    )
    preflight = preflight_mapped_records(doctype, normalized)

    return {
        "passed": not preflight.get("blocking"),
        "field_mapping": field_mapping,
        "preflight": preflight,
        "record_count": len(normalized),
        "methods": methods,
        "missing_required_after": preflight.get("missing_fields") or [],
    }
