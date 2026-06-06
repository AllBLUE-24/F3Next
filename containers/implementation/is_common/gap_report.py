"""Unified GapItem builders for readiness, mapping, validate, and LER."""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from shared.gate_contracts import GapItem, GapSeverity

GapOrigin = Literal["readiness", "mapping_preflight", "validate", "ler", "live_erp"]
GapResolution = Literal["default", "ask_user", "upload", "pipeline_fix", "defer_import"]
GapTier = Literal["critical", "important", "info"]


def _meta(
    *,
    origin: GapOrigin,
    tier: GapTier = "critical",
    resolution: GapResolution = "ask_user",
    source_file: Optional[str] = None,
    missing_fields: Optional[List[str]] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    meta: Dict[str, Any] = {
        "origin": origin,
        "tier": tier,
        "resolution": resolution,
    }
    if source_file:
        meta["source_file"] = source_file
    if missing_fields:
        meta["missing_fields"] = list(missing_fields)
    if extra:
        meta.update(extra)
    return meta


def make_gap_item(
    *,
    field: str,
    question: str,
    doctype: Optional[str] = None,
    severity: GapSeverity = "blocking",
    origin: GapOrigin = "readiness",
    tier: GapTier = "critical",
    resolution: GapResolution = "ask_user",
    source_file: Optional[str] = None,
    missing_fields: Optional[List[str]] = None,
    rule_id: Optional[str] = None,
    candidates: Optional[List[str]] = None,
    extra_metadata: Optional[Dict[str, Any]] = None,
) -> GapItem:
    return GapItem(
        field=field,
        question=question,
        severity=severity,
        candidates=list(candidates or []),
        rule_id=rule_id,
        doctype=doctype,
        metadata=_meta(
            origin=origin,
            tier=tier,
            resolution=resolution,
            source_file=source_file,
            missing_fields=missing_fields,
            extra=extra_metadata,
        ),
    )


def gap_from_preflight_block(block: Dict[str, Any]) -> GapItem:
    doctype = str(block.get("doctype") or "Unknown")
    source_file = str(block.get("source_file") or "")
    missing = list(block.get("missing_fields") or [])
    messages = block.get("messages") or []
    question = (
        messages[0]
        if messages
        else (
            f"{doctype} could not be mapped from {source_file or 'your file'} — "
            f"required fields missing: {', '.join(missing) or 'unknown'}."
        )
    )
    return make_gap_item(
        field=missing[0] if missing else doctype,
        question=question,
        doctype=doctype,
        severity="blocking",
        origin="mapping_preflight",
        tier="critical",
        resolution="upload",
        source_file=source_file or None,
        missing_fields=missing,
        rule_id="mapping_preflight_blocking",
    )


def gap_from_dry_run_failure(entry: Dict[str, Any]) -> GapItem:
    doctype = str(entry.get("doctype") or "Unknown")
    source_file = str(entry.get("source_file") or "")
    dry_run = entry.get("dry_run") or {}
    missing = list(
        dry_run.get("missing_required_after")
        or dry_run.get("preflight", {}).get("missing_fields")
        or entry.get("blocking_fields")
        or entry.get("missing_required_fields")
        or []
    )
    return make_gap_item(
        field=missing[0] if missing else doctype,
        question=(
            f"{doctype} data in {source_file or 'uploaded file'} cannot be mapped yet — "
            f"missing: {', '.join(missing) or 'required fields'}."
        ),
        doctype=doctype,
        severity="blocking",
        origin="readiness",
        tier="important" if entry.get("ready_with_assumptions") else "critical",
        resolution="upload",
        source_file=source_file or None,
        missing_fields=missing,
        rule_id="readiness_dry_run_failed",
    )


def gap_from_ler_info(
    *,
    link_target: str,
    value: str,
    doctype: str,
    field: str,
) -> GapItem:
    return make_gap_item(
        field=field,
        question=(
            f"{link_target} '{value}' is not on your live ERP site yet — it will be created "
            f"when master data is imported in this session before transactional records."
        ),
        doctype=doctype,
        severity="hint",
        origin="ler",
        tier="info",
        resolution="defer_import",
        rule_id="ler_greenfield_covered",
        extra_metadata={"link_target": link_target, "value": value},
    )


def gaps_from_pre_analysis(pre_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Build unified GapItem dicts from deterministic readiness scan."""
    items: List[GapItem] = []

    for entry in pre_analysis.get("partial_doctypes") or []:
        if not isinstance(entry, dict):
            continue
        if entry.get("dry_run_failed") or entry.get("dry_run_passed") is False:
            items.append(gap_from_dry_run_failure(entry))

    for entry in pre_analysis.get("missing_doctypes") or []:
        if not isinstance(entry, dict):
            continue
        doctype = str(entry.get("doctype") or "")
        missing = list(entry.get("missing_required_fields") or entry.get("blocking_fields") or [])
        items.append(
            make_gap_item(
                field=missing[0] if missing else doctype,
                question=f"No uploaded file covers {doctype}.",
                doctype=doctype,
                severity="blocking",
                origin="readiness",
                tier="critical",
                resolution="upload",
                missing_fields=missing,
                rule_id="readiness_missing_doctype",
            )
        )

    return [g.to_dict() for g in items]


def merge_gap_item_dicts(*groups: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Dedupe by (origin, doctype, field)."""
    seen: set[tuple[str, str, str]] = set()
    out: List[Dict[str, Any]] = []
    for group in groups:
        for raw in group or []:
            if not isinstance(raw, dict):
                continue
            origin = str((raw.get("metadata") or {}).get("origin") or "")
            doctype = str(raw.get("doctype") or "")
            field = str(raw.get("field") or "")
            key = (origin, doctype, field)
            if key in seen:
                continue
            seen.add(key)
            out.append(raw)
    return out


def open_critical_gaps(gap_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [
        g for g in gap_items
        if str((g.get("metadata") or {}).get("tier", "")).lower() == "critical"
        and str(g.get("severity", "blocking")).lower() in ("blocking", "")
    ]
