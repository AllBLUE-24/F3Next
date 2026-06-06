"""Explicit MVP × file × field provability matrix for Step 8c."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple

from containers.implementation.data_readiness_agent.field_policy import assess_field_coverage
from containers.implementation.mapping_agent.dry_run_map import dry_run_map_file

_EVIDENCE_THRESHOLD = 0.10


def _corpus_claims_by_file(corpus_understanding: Optional[Dict[str, Any]]) -> Dict[str, Set[str]]:
    claims: Dict[str, Set[str]] = {}
    if not corpus_understanding:
        return claims
    for entry in corpus_understanding.get("files") or []:
        if not isinstance(entry, dict):
            continue
        fname = entry.get("filename") or ""
        if not fname:
            continue
        claims.setdefault(fname, set())
        for dt in entry.get("likely_erpnext_doctypes") or []:
            if dt:
                claims[fname].add(str(dt))
    return claims


def _column_evidence_score(
    fname: str,
    columns: List[str],
    doctype: str,
    kb: Dict[str, Any],
    *,
    score_fn,
    boost_fn,
) -> Tuple[float, List[str], List[str]]:
    if columns:
        score, matched, missing = score_fn(columns, doctype, kb)
    else:
        score, matched, missing = 0.0, [], []
    score += boost_fn(fname, doctype)
    return score, matched, missing


def assess_file_doctype_matrix(
    *,
    files: Dict[str, str],
    file_meta: Dict[str, Dict],
    scope_doctypes: List[str],
    field_mappings_kb: Dict[str, Any],
    corpus_understanding: Optional[Dict[str, Any]] = None,
    party_evidence: Optional[Dict[str, Dict[str, Any]]] = None,
    corpus_hits: Optional[Dict[str, List[str]]] = None,
    ready_pairs: Optional[Set[Tuple[str, str]]] = None,
    f3iche_id: Optional[str] = None,
    score_columns_fn,
    keyword_score_fn,
    filename_boost_fn,
    party_split_for_doctype=None,
) -> Dict[str, Any]:
    """
    Build per (file, doctype) matrix: claimed | evidenced | provable | ready.

    Returns {rows: [...], overclaims: [...], summary: {...}}
    """
    scope_set = set(scope_doctypes or [])
    corpus_claims = _corpus_claims_by_file(corpus_understanding)
    hits = corpus_hits or {}
    ready_pairs = ready_pairs or set()
    party_evidence = party_evidence or {}
    rows: List[Dict[str, Any]] = []
    overclaims: List[Dict[str, Any]] = []

    candidate_pairs: Set[Tuple[str, str]] = set()
    for fname in file_meta:
        for dt in scope_set:
            candidate_pairs.add((fname, dt))
        for dt in corpus_claims.get(fname, set()):
            candidate_pairs.add((fname, dt))

    for fname, doctype in sorted(candidate_pairs):
        meta = file_meta.get(fname) or {}
        columns = meta.get("columns") or []
        content = files.get(fname) or ""

        in_mvp = doctype in scope_set
        claimed = doctype in corpus_claims.get(fname, set())

        col_score, matched, missing = _column_evidence_score(
            fname, columns, doctype, field_mappings_kb,
            score_fn=score_columns_fn,
            boost_fn=filename_boost_fn,
        )
        party_hit = doctype in party_evidence and party_evidence[doctype].get("source_file") == fname
        corpus_hit = fname in (hits.get(doctype) or [])
        evidenced = (
            col_score >= _EVIDENCE_THRESHOLD
            or party_hit
            or (corpus_hit and col_score > 0)
        )

        policy = assess_field_coverage(
            doctype, matched, columns, field_mappings_kb, f3iche_id=f3iche_id,
        )
        defaultable = bool(policy.get("can_proceed_without")) and bool(policy.get("assumption_only"))

        provable = False
        dry_run: Dict[str, Any] = {}
        if content and (evidenced or party_hit):
            if party_hit and party_split_for_doctype:
                dry_run = dry_run_map_file(content, doctype, kb=field_mappings_kb)
            else:
                dry_run = dry_run_map_file(
                    content,
                    doctype,
                    kb=field_mappings_kb,
                    company_context={"company_name": "Session Company"},
                )
            provable = bool(dry_run.get("passed"))

        ready = (fname, doctype) in ready_pairs
        corpus_overclaim = claimed and not evidenced

        row = {
            "filename": fname,
            "doctype": doctype,
            "in_mvp_scope": in_mvp,
            "corpus_claims": claimed,
            "file_evidence_score": round(col_score, 3),
            "evidenced": evidenced,
            "field_provable": provable,
            "defaultable": defaultable,
            "ready": ready,
            "corpus_overclaim": corpus_overclaim,
            "matched_fields": matched,
            "missing_fields": missing,
            "dry_run_passed": dry_run.get("passed") if dry_run else None,
        }
        rows.append(row)

        if corpus_overclaim and in_mvp:
            overclaims.append({
                "filename": fname,
                "doctype": doctype,
                "reason": (
                    f"Corpus claimed {doctype} for {fname} but column/filename evidence "
                    f"score {col_score:.2f} is below threshold."
                ),
            })

    n_provable = sum(1 for r in rows if r["field_provable"] and r["in_mvp_scope"])
    n_overclaim = len(overclaims)

    return {
        "rows": rows,
        "overclaims": overclaims,
        "summary": {
            "pairs_assessed": len(rows),
            "mvp_pairs": sum(1 for r in rows if r["in_mvp_scope"]),
            "corpus_overclaims": n_overclaim,
            "field_provable_mvp": n_provable,
        },
    }
