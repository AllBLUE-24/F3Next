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
    # New: column context for better UX
    user_columns: Optional[List[str]] = None,
    attempted_synonyms: Optional[List[str]] = None,
    working_synonyms: Optional[List[str]] = None,
    mapping_methods: Optional[Dict[str, str]] = None,
) -> GapItem:
    metadata = _meta(
        origin=origin,
        tier=tier,
        resolution=resolution,
        source_file=source_file,
        missing_fields=missing_fields,
        extra=extra_metadata,
    )
    # Enrich with column context
    if user_columns:
        metadata["user_columns"] = list(user_columns)
    if attempted_synonyms:
        metadata["attempted_synonyms"] = list(attempted_synonyms)
    if working_synonyms:
        metadata["working_synonyms"] = list(working_synonyms)
    if mapping_methods:
        metadata["mapping_methods"] = dict(mapping_methods)
    
    return GapItem(
        field=field,
        question=question,
        severity=severity,
        candidates=list(candidates or []),
        rule_id=rule_id,
        doctype=doctype,
        metadata=metadata,
    )


def gap_from_preflight_block(block: Dict[str, Any]) -> GapItem:
    doctype = str(block.get("doctype") or "Unknown")
    source_file = str(block.get("source_file") or "")
    missing = list(block.get("missing_fields") or [])
    messages = block.get("messages") or []
    user_columns = list(block.get("user_columns") or [])
    field_mapping = block.get("field_mapping") or {}
    mapping_methods = block.get("mapping_methods") or {}
    
    # Build enhanced question with column context
    question_parts = []
    if source_file:
        question_parts.append(f"In your file **{source_file}**")
    else:
        question_parts.append("In your uploaded file")
    
    if missing:
        if len(missing) == 1:
            question_parts.append(f"we couldn't find a column for the required field **{missing[0]}**")
        else:
            question_parts.append(f"we couldn't find columns for {len(missing)} required fields: {', '.join(missing[:3])}")
    else:
        question_parts.append(f"the {doctype} data could not be mapped correctly")
    
    # Add column context if available
    if user_columns:
        question_parts.append(f"Your columns are: {', '.join(user_columns[:8])}")
        if len(user_columns) > 8:
            question_parts.append(f"(and {len(user_columns) - 8} more)")
    
    # Suggest working column names
    if missing:
        from containers.implementation.mapping_agent.kb import field_mappings as _kb
        kb = _kb()
        dt_cfg = (kb.get("doctypes") or {}).get(doctype) or {}
        fmap = dt_cfg.get("field_mappings") or {}
        working = []
        for m_field in missing[:3]:
            cfg = fmap.get(m_field) or {}
            syns = list(cfg.get("user_input_synonyms") or [])[:3]
            if syns:
                working.extend(syns)
        if working:
            question_parts.append(f"Try using column names like: {', '.join(list(dict.fromkeys(working))[:5])}")
    
    question = ". ".join(question_parts) + "."
    
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
        user_columns=user_columns,
        mapping_methods=mapping_methods,
        working_synonyms=working[:5] if working else None,
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
    user_columns = list(entry.get("columns") or dry_run.get("columns") or [])
    field_mapping = dry_run.get("field_mapping") or {}
    mapping_methods = dry_run.get("methods") or {}
    
    # Build context-rich question
    question_parts = []
    if source_file:
        question_parts.append(f"File **{source_file}** contains {doctype} data")
    else:
        question_parts.append(f"Your uploaded file contains {doctype} data")
    
    if missing:
        question_parts.append(f"but we couldn't map these required fields: {', '.join(missing[:4])}")
    else:
        question_parts.append("but some required fields couldn't be mapped")
    
    if user_columns:
        successfully_mapped = [c for c in user_columns if c in field_mapping]
        if successfully_mapped:
            question_parts.append(
                f"We successfully mapped: {', '.join(successfully_mapped[:4])}. "
            )
        question_parts.append(f"Your columns: {', '.join(user_columns[:6])}")
    
    question = ". ".join(question_parts) + "."
    
    return make_gap_item(
        field=missing[0] if missing else doctype,
        question=question,
        doctype=doctype,
        severity="blocking",
        origin="readiness",
        tier="important" if entry.get("ready_with_assumptions") else "critical",
        resolution="upload",
        source_file=source_file or None,
        missing_fields=missing,
        rule_id="readiness_dry_run_failed",
        user_columns=user_columns,
        mapping_methods=mapping_methods,
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
            f"{link_target} '{value}' will be created from your uploaded data during "
            f"master import before transactional records."
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
