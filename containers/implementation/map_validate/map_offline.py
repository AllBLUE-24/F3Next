"""Offline deterministic mapping for Step 4 harness."""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from containers.implementation.mapping_agent.corpus_merge import merge_record_lists
from containers.implementation.mapping_agent.dry_run_map import dry_run_map_file
from containers.implementation.map_validate.inputs import MapValidateInputs
from containers.implementation.map_validate.models import MapResultRow


def _party_filter_factory(doctype: str):
    from containers.implementation.mapping_agent.dry_run_map import _filter_party_rows

    def _filter(rows, columns):
        return _filter_party_rows(rows, columns, doctype)

    return _filter


def run_offline_mapping(inputs: MapValidateInputs) -> tuple[List[MapResultRow], Dict[str, Any]]:
    """
    Dry-run map each (file, doctype) pair and merge records per doctype.

    Returns (map_results, mapped_data) where mapped_data is {doctype: {records: [...]}}.
    """
    kb = inputs.field_mappings_kb
    ctx = inputs.company_context
    by_doctype_records: Dict[str, List[Dict[str, Any]]] = {}
    results: List[MapResultRow] = []

    for fname, doctype in inputs.file_doctype_pairs:
        content = inputs.files.get(fname) or ""
        if not content:
            continue
        row_filter = _party_filter_factory(doctype) if doctype in ("Customer", "Supplier") else None
        dr = dry_run_map_file(
            content,
            doctype,
            kb=kb,
            row_filter=row_filter,
            company_context=ctx,
            project_id=inputs.project_id,
        )
        preflight = dr.get("preflight") or {}
        results.append(
            MapResultRow(
                filename=fname,
                doctype=doctype,
                passed=bool(dr.get("passed")),
                record_count=int(dr.get("record_count") or 0),
                field_mapping=dict(dr.get("field_mapping") or {}),
                mapping_methods=dict(dr.get("methods") or {}),
                missing_fields=list(preflight.get("missing_fields") or dr.get("missing_required_after") or []),
                messages=list(preflight.get("messages") or []),
            )
        )
        if dr.get("passed") and dr.get("records"):
            existing = by_doctype_records.setdefault(doctype, [])
            by_doctype_records[doctype] = merge_record_lists(doctype, existing, list(dr["records"]))

    mapped_data = {dt: {"records": recs} for dt, recs in by_doctype_records.items() if recs}
    return results, mapped_data
