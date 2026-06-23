"""Build import preview checklist from validation ler_gaps and mapped payloads."""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def _row_count(mapped_data: Dict[str, Any], doctype: str) -> int:
    payload = mapped_data.get(doctype) or {}
    records = payload.get("records") or []
    return len(records) if isinstance(records, list) else 0


def _source_files(mapped_data: Dict[str, Any], doctype: str) -> List[str]:
    payload = mapped_data.get(doctype) or {}
    sources = payload.get("source_files") or []
    if sources:
        return [str(s) for s in sources if s]
    src = payload.get("source_file")
    return [str(src)] if src else []


def build_import_preview(
    *,
    ler_gaps: List[Dict[str, Any]],
    mapped_data: Optional[Dict[str, Any]] = None,
    bootstrap_summary: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Structured MSME-facing import preview.

    will_create_on_erp — masters/transactions/config deferred to import
    needs_your_ok — blocking link values requiring map or auto-fix
    """
    mapped = mapped_data or {}
    will_create: List[Dict[str, Any]] = []
    needs_ok: List[Dict[str, Any]] = []
    seen_will: set = set()
    seen_block: set = set()

    for gap in ler_gaps or []:
        if not isinstance(gap, dict):
            continue
        severity = str(gap.get("severity") or "blocking").lower()
        meta = gap.get("metadata") or {}
        field = str(gap.get("field") or meta.get("field") or "")
        doctype = str(gap.get("doctype") or meta.get("doctype") or "")
        link_target = str(
            meta.get("link_target") or meta.get("target_doctype") or field or doctype
        )
        value = str(meta.get("value") or "")
        key = (severity, link_target, value, doctype)

        if severity == "hint":
            if key in seen_will:
                continue
            seen_will.add(key)
            will_create.append({
                "doctype": link_target or doctype,
                "field": field,
                "value": value,
                "source_doctype": doctype,
                "row_count": _row_count(mapped, link_target or doctype),
                "source_files": _source_files(mapped, doctype),
                "message": gap.get("question") or gap.get("message") or "",
            })
        elif severity == "blocking":
            if key in seen_block:
                continue
            seen_block.add(key)
            needs_ok.append({
                "doctype": link_target or doctype,
                "field": field,
                "value": value,
                "source_doctype": doctype,
                "row_count": _row_count(mapped, doctype),
                "message": gap.get("question") or gap.get("message") or "",
                "candidates": list(gap.get("candidates") or []),
            })

    if bootstrap_summary:
        derived = bootstrap_summary.get("derived_config") or {}
        for config_dt, payload in derived.items():
            if not isinstance(payload, dict):
                continue
            records = payload.get("records") or []
            if not records:
                continue
            key = ("bootstrap", config_dt, "", "")
            if key in seen_will:
                continue
            seen_will.add(key)
            will_create.append({
                "doctype": config_dt,
                "field": "",
                "value": "",
                "source_doctype": config_dt,
                "row_count": len(records),
                "source_files": ["site_config_bootstrap"],
                "message": (
                    f"{len(records)} {config_dt} record(s) will be created in site config "
                    "phase before master import."
                ),
            })

    return {
        "will_create_on_erp": will_create,
        "needs_your_ok": needs_ok,
    }
