"""MVP × file × field readiness matrix."""
from __future__ import annotations

from typing import Any, Dict, List, Set, Tuple

from containers.implementation.data_readiness_agent.field_policy import assess_field_coverage
from containers.implementation.data_readiness_agent.gap_analyzer import (
    _filename_prior_boost,
    _keyword_score_text,
    _resolve_scope_doctypes,
    _score_columns_vs_doctype,
    analyze_gaps,
    normalize_manifest_input,
)
from containers.implementation.data_readiness_agent.file_doctype_matrix import (
    assess_file_doctype_matrix,
)
from containers.implementation.readiness.inputs import ReadinessInputs
from containers.implementation.readiness.models import MatrixRow, ReadinessMatrix
from containers.implementation.readiness.schema import resolve_required_fields


def _row_status(
    *,
    in_mvp: bool,
    deferred: bool,
    ready: bool,
    evidenced: bool,
    corpus_overclaim: bool,
    blocking_fields: List[str],
    field_provable: bool,
) -> str:
    if deferred:
        return "deferred"
    if corpus_overclaim and in_mvp:
        return "overclaim"
    if ready or (field_provable and not blocking_fields):
        return "ready"
    if evidenced or blocking_fields:
        return "partial"
    if in_mvp:
        return "missing"
    return "info"


def _scope_doctypes(target: Dict[str, Any], pre_analysis: Dict[str, Any]) -> List[str]:
    scope, _ = _resolve_scope_doctypes(target)
    seen = set(scope)
    for bucket in ("ready_doctypes", "partial_doctypes", "missing_doctypes"):
        for entry in pre_analysis.get(bucket) or []:
            if isinstance(entry, dict):
                dt = entry.get("doctype")
                if dt and dt not in seen:
                    seen.add(dt)
                    scope.append(dt)
    return scope


def build_readiness_matrix(inputs: ReadinessInputs) -> tuple[ReadinessMatrix, Dict[str, Any], Dict[str, str]]:
    """
    Build matrix rows by merging Step 2 file assignment with gap analyzer output.

    Returns (matrix, pre_analysis, schema_sources).
    """
    manifest = inputs.manifest
    target = inputs.target_structure
    kb = inputs.field_mappings_kb
    f3iche_id = inputs.f3iche_id
    deferred = set(target.get("deferred_doctypes") or [])

    pre_analysis = analyze_gaps(
        manifest,
        target,
        kb,
        f3iche_id=f3iche_id,
    )
    scope_doctypes = _scope_doctypes(target, pre_analysis)

    raw_matrix = pre_analysis.get("file_doctype_matrix")
    if not raw_matrix:
        files, prebuilt_meta, corpus_understanding = normalize_manifest_input(manifest)
        ready_pairs: Set[Tuple[str, str]] = set()
        for entry in pre_analysis.get("ready_doctypes") or []:
            if isinstance(entry, dict) and entry.get("source_file") and entry.get("doctype"):
                ready_pairs.add((entry["source_file"], entry["doctype"]))
        file_meta: Dict[str, Dict] = {}
        for fname, content in files.items():
            pre = prebuilt_meta.get(fname) or {}
            file_meta[fname] = {
                "filename": fname,
                "columns": pre.get("columns") or [],
                "is_structured": pre.get("is_structured", True),
                "content_snippet": (content or "")[:1500],
            }
        raw_matrix = assess_file_doctype_matrix(
            files=files,
            file_meta=file_meta,
            scope_doctypes=scope_doctypes,
            field_mappings_kb=kb,
            corpus_understanding=corpus_understanding,
            ready_pairs=ready_pairs,
            f3iche_id=f3iche_id,
            score_columns_fn=_score_columns_vs_doctype,
            keyword_score_fn=_keyword_score_text,
            filename_boost_fn=_filename_prior_boost,
        )

    files, prebuilt_meta, _ = normalize_manifest_input(manifest)
    file_meta: Dict[str, Dict] = {}
    for fname in files:
        pre = prebuilt_meta.get(fname) or {}
        file_meta[fname] = {"columns": pre.get("columns") or []}

    schema_sources: Dict[str, str] = {}
    required_by_doctype: Dict[str, List[str]] = {}
    for doctype in scope_doctypes:
        required, source = resolve_required_fields(
            doctype,
            project_id=inputs.project_id,
            f3iche_id=f3iche_id,
        )
        required_by_doctype[doctype] = required
        schema_sources[doctype] = source

    rows: List[MatrixRow] = []
    for raw in raw_matrix.get("rows") or []:
        if not isinstance(raw, dict):
            continue
        doctype = str(raw.get("doctype") or "")
        fname = str(raw.get("filename") or "")
        columns = (file_meta.get(fname) or {}).get("columns") or []
        matched = list(raw.get("matched_fields") or [])
        policy = assess_field_coverage(
            doctype,
            matched,
            columns,
            kb,
            f3iche_id=f3iche_id,
        )
        required = required_by_doctype.get(doctype, [])
        present = list(dict.fromkeys(matched))
        blocking = list(policy.get("blocking_fields") or [])
        missing = [f for f in required if f not in present]
        if blocking:
            missing = list(dict.fromkeys(missing + blocking))

        in_mvp = bool(raw.get("in_mvp_scope"))
        is_deferred = doctype in deferred
        status = _row_status(
            in_mvp=in_mvp,
            deferred=is_deferred,
            ready=bool(raw.get("ready")),
            evidenced=bool(raw.get("evidenced")),
            corpus_overclaim=bool(raw.get("corpus_overclaim")),
            blocking_fields=blocking,
            field_provable=bool(raw.get("field_provable")),
        )
        rows.append(
            MatrixRow(
                filename=fname,
                doctype=doctype,
                in_mvp_scope=in_mvp,
                corpus_claims=bool(raw.get("corpus_claims")),
                evidenced=bool(raw.get("evidenced")),
                field_provable=bool(raw.get("field_provable")),
                ready=bool(raw.get("ready")),
                corpus_overclaim=bool(raw.get("corpus_overclaim")),
                required_fields=required,
                present_fields=present,
                missing_fields=missing,
                assumed_fields=policy.get("assumed_fields") or [],
                blocking_fields=blocking,
                status=status,  # type: ignore[arg-type]
                file_evidence_score=float(raw.get("file_evidence_score") or 0.0),
            )
        )

    matrix = ReadinessMatrix(
        rows=rows,
        overclaims=list(raw_matrix.get("overclaims") or []),
        summary=dict(raw_matrix.get("summary") or {}),
    )
    return matrix, pre_analysis, schema_sources
