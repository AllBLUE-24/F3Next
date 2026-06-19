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
    scoped_doctypes: Optional[set[str]] = None,
) -> Dict[str, str]:
    tier1 = engine.map_columns(columns, doctype, sample_row=sample_row)
    merged = kb_fuzzy_map_columns(columns, doctype, kb, already_mapped=tier1)
    from containers.implementation.is_common.link_scope_policy import filter_field_mapping

    filtered, _ = filter_field_mapping(merged, doctype, kb, scoped_doctypes=scoped_doctypes)
    return filtered


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


def _dry_run_llm_enabled() -> bool:
    return os.getenv("IS_DRY_RUN_LLM", "0").strip().lower() in ("1", "true", "yes")


async def dry_run_map_file_async(
    content: str,
    doctype: str,
    *,
    kb: Dict[str, Any],
    row_filter: Optional[Callable[[List[Dict[str, Any]], List[str]], List[Dict[str, Any]]]] = None,
    company_context: Optional[Dict[str, Any]] = None,
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Dry-run with full tiered mapping (KB → LLM → fuzzy) when IS_DRY_RUN_LLM=1."""
    from containers.implementation.mapping_agent.column_map_tiered import map_columns_tiered
    from containers.implementation.mapping_agent.schema_resolver import resolve_kb_gaps_sync
    from containers.implementation.mapping_agent.synonym_promotion import suggest_synonym_promotions

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

    effective_kb, resolver_meta = resolve_kb_gaps_sync(doctype, kb)
    engine = _MappingEngine()
    engine._field_mappings = effective_kb
    field_mapping, audit = await map_columns_tiered(
        engine,
        columns,
        doctype,
        sample_rows=rows,
        kb=effective_kb,
    )
    methods = dict(audit.get("methods") or {})

    mapped = _apply_field_mapping(rows, field_mapping)
    folded = fold_child_tables(doctype, mapped)
    normalized = apply_defaults_and_normalize(
        doctype, folded, context=company_context or {},
    )
    preflight = preflight_mapped_records(doctype, normalized)
    missing_required = preflight.get("missing_fields") or []
    synonym_promotions = suggest_synonym_promotions(
        doctype=doctype,
        field_mapping=field_mapping,
        columns=columns,
        missing_required=missing_required,
    )

    return {
        "passed": not preflight.get("blocking"),
        "field_mapping": field_mapping,
        "preflight": preflight,
        "record_count": len(normalized),
        "methods": methods,
        "missing_required_after": missing_required,
        "schema_resolver": resolver_meta,
        "synonym_promotions": synonym_promotions,
        "project_id": project_id,
        "dry_run_mode": "tiered_llm",
    }


def dry_run_map_file(
    content: str,
    doctype: str,
    *,
    kb: Dict[str, Any],
    row_filter: Optional[Callable[[List[Dict[str, Any]], List[str]], List[Dict[str, Any]]]] = None,
    company_context: Optional[Dict[str, Any]] = None,
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run map → fold → defaults → preflight without persisting.

    Uses Tier 1 KB exact + Tier 3 KB fuzzy by default.
    Set IS_DRY_RUN_LLM=1 for Tier 2 LLM in legacy field-level readiness mode.
    """
    if _dry_run_llm_enabled():
        import asyncio

        return asyncio.run(
            dry_run_map_file_async(
                content,
                doctype,
                kb=kb,
                row_filter=row_filter,
                company_context=company_context,
                project_id=project_id,
            )
        )

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

    from containers.implementation.mapping_agent.schema_resolver import resolve_kb_gaps_sync
    from containers.implementation.mapping_agent.synonym_promotion import suggest_synonym_promotions

    effective_kb, resolver_meta = resolve_kb_gaps_sync(doctype, kb)

    engine = _MappingEngine()
    engine._field_mappings = effective_kb
    field_mapping = _map_columns_deterministic(
        engine, columns, doctype, effective_kb, sample_row=rows[0],
    )
    methods = {src: "kb_local" for src in field_mapping}

    mapped = _apply_field_mapping(rows, field_mapping)
    folded = fold_child_tables(doctype, mapped)
    normalized = apply_defaults_and_normalize(
        doctype, folded, context=company_context or {},
    )
    preflight = preflight_mapped_records(doctype, normalized)
    missing_required = preflight.get("missing_fields") or []
    synonym_promotions = suggest_synonym_promotions(
        doctype=doctype,
        field_mapping=field_mapping,
        columns=columns,
        missing_required=missing_required,
    )

    return {
        "passed": not preflight.get("blocking"),
        "field_mapping": field_mapping,
        "preflight": preflight,
        "record_count": len(normalized),
        "methods": methods,
        "missing_required_after": missing_required,
        "schema_resolver": resolver_meta,
        "synonym_promotions": synonym_promotions,
        "project_id": project_id,
    }
