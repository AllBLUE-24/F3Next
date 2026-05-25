"""Corpus merge utilities — dedupe and union records across multi-file uploads."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Sequence

from containers.knowledge_base.erpnext.schema.compose import merge_policies

_RAW_KEY_ALIASES: Dict[str, List[str]] = {
    "supplier_name": ["supplier_name", "party_name", "name", "vendor_name"],
    "customer_name": ["customer_name", "party_name", "name", "client_name"],
    "item_code": ["item_code", "item code", "sku", "code"],
    "item": ["item", "fg_item", "finished_good"],
    "project_name": ["project_name", "project name", "project", "project_id"],
}


def dedupe_key_for(doctype: str) -> Optional[str]:
    policies = merge_policies()
    key = (policies.get("dedupe_key") or {}).get(doctype)
    return str(key) if key else None


def record_richness(record: Dict[str, Any]) -> int:
    return sum(
        1
        for v in record.values()
        if v not in (None, "", [], {})
    )


def _norm_key(val: Any) -> str:
    return str(val or "").strip().lower()


def _row_dedupe_key(doctype: str, row: Dict[str, Any]) -> str:
    key_field = dedupe_key_for(doctype)
    if not key_field:
        return ""
    if row.get(key_field):
        return _norm_key(row[key_field])
    for alias in _RAW_KEY_ALIASES.get(key_field, []):
        if row.get(alias):
            return _norm_key(row[alias])
    return ""


def merge_record_lists(
    doctype: str,
    existing: List[Dict[str, Any]],
    incoming: List[Dict[str, Any]],
    *,
    strategy: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Union records for a doctype, deduping by KB merge policy."""
    policies = merge_policies()
    strategy = strategy or policies.get("merge_strategy", "union_richest_first")
    key_field = dedupe_key_for(doctype)

    if not key_field:
        return list(existing) + list(incoming)

    merged: Dict[str, Dict[str, Any]] = {}
    order: List[str] = []

    for rec in list(existing) + list(incoming):
        if not isinstance(rec, dict):
            continue
        k = _row_dedupe_key(doctype, rec) or f"__anon_{len(order)}"
        if k in merged:
            if strategy == "union_richest_first":
                existing_rec = merged[k]
                new_rich = record_richness(rec)
                old_rich = record_richness(existing_rec)
                if new_rich > old_rich:
                    merged[k] = rec
                elif new_rich == old_rich:
                    combined = dict(existing_rec)
                    for fk, fv in rec.items():
                        if fv not in (None, "", [], {}) and combined.get(fk) in (None, "", [], {}):
                            combined[fk] = fv
                    merged[k] = combined
            else:
                merged[k] = rec
        else:
            merged[k] = rec
            order.append(k)

    return [merged[k] for k in order if k in merged]


def merge_payloads(
    doctype: str,
    existing_payload: Optional[Dict[str, Any]],
    incoming_payload: Dict[str, Any],
) -> Dict[str, Any]:
    existing_records = (existing_payload or {}).get("records") or []
    incoming_records = incoming_payload.get("records") or []
    merged_records = merge_record_lists(doctype, existing_records, incoming_records)

    out = dict(incoming_payload)
    if existing_payload:
        existing_lf = existing_payload.get("link_fields") or {}
        incoming_lf = incoming_payload.get("link_fields") or {}
        out["link_fields"] = {**existing_lf, **incoming_lf}
    out["records"] = merged_records
    out["doctype"] = doctype
    return out


def merge_extracted_rows(
    doctype: str,
    existing_rows: List[Dict[str, Any]],
    incoming_rows: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    return merge_record_lists(doctype, existing_rows, incoming_rows)


def load_r2_json(s3: Any, bucket: str, key: str) -> Any:
    try:
        resp = s3.get_object(Bucket=bucket, Key=key)
        return json.loads(resp["Body"].read().decode("utf-8"))
    except Exception:
        return None


def aggregate_mapped_data_rows(mapped_rows: Sequence[Any]) -> Dict[str, Dict[str, Any]]:
    """Aggregate ISMappedData rows by target_doctype (shared canonical R2 path)."""
    by_dt: Dict[str, Dict[str, Any]] = {}
    for m in mapped_rows:
        dt = m.target_doctype
        if dt not in by_dt:
            by_dt[dt] = {
                "r2_path": m.mapped_payload_r2_path,
                "total_rows": m.total_rows or 0,
                "validation_status": m.validation_status or "pending",
                "source_files": [m.source_filename] if m.source_filename else [],
            }
            continue

        entry = by_dt[dt]
        entry["total_rows"] += m.total_rows or 0
        if m.source_filename and m.source_filename not in entry["source_files"]:
            entry["source_files"].append(m.source_filename)
        if m.validation_status == "failed":
            entry["validation_status"] = "failed"
        elif entry["validation_status"] not in ("failed",) and m.validation_status == "passed":
            entry["validation_status"] = "passed"
    return by_dt


def enrich_mapped_dict_from_r2(
    mapped_dict: Dict[str, Dict[str, Any]],
    s3: Any,
    *,
    bucket: str = "clean-data",
) -> Dict[str, Dict[str, Any]]:
    """Replace total_rows with deduped record count from canonical merged R2 payload."""
    for dt, info in mapped_dict.items():
        r2_path = info.get("r2_path")
        if not r2_path:
            continue
        payload = load_r2_json(s3, bucket, r2_path)
        if isinstance(payload, dict):
            records = payload.get("records") or []
            info["total_rows"] = len(records)
            info["merged_record_count"] = len(records)
    return mapped_dict


_DOCTYPE_PHASE: Dict[str, str] = {
    "Item": "phase_b_master",
    "Customer": "phase_b_master",
    "Supplier": "phase_b_master",
    "BOM": "phase_b_master",
    "Batch": "phase_b_master",
    "Employee": "phase_b_master",
    "Project": "phase_d_projects",
    "Work Order": "phase_c_transactional",
    "Purchase Receipt": "phase_c_transactional",
    "Stock Entry": "phase_c_transactional",
    "Purchase Order": "phase_c_transactional",
    "Sales Order": "phase_c_transactional",
    "Sales Invoice": "phase_c_transactional",
    "Payment Entry": "phase_c_transactional",
    "Journal Entry": "phase_c_transactional",
}

_PHASE_LABELS: Dict[str, str] = {
    "phase_d_projects": "Project Data",
}


def inject_missing_mapped_steps(
    phases: Dict[str, Any],
    mapped_dict: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """Append import-plan steps for mapped doctypes missing from the blueprint."""
    planned = {
        step.get("doctype")
        for phase_data in phases.values()
        for step in (phase_data.get("steps") or [])
        if step.get("doctype")
    }

    updated = dict(phases)
    for dt, info in mapped_dict.items():
        if dt in planned or (info.get("total_rows") or 0) <= 0:
            continue

        phase_key = _DOCTYPE_PHASE.get(dt, "phase_c_transactional")
        if phase_key not in updated:
            updated[phase_key] = {
                "name": _PHASE_LABELS.get(phase_key, phase_key.replace("_", " ").title()),
                "steps": [],
            }

        steps = list(updated[phase_key].get("steps") or [])
        steps.append(
            {
                "step": len(steps) + 1,
                "doctype": dt,
                "action": "create",
                "data_source": info.get("r2_path"),
                "records": info.get("total_rows") or 0,
            }
        )
        updated[phase_key] = {**updated[phase_key], "steps": steps}

    return updated
