"""
data_readiness_agent/gap_analyzer.py

Deterministic pre-LLM gap analysis.

Given:
  - manifest: {filename: content_or_columns} from R2
  - target_structure: ISTargetStructure result (seed_doctypes, required_doctypes, setup_steps)
  - field_mappings_kb: the field_mappings.json knowledge base

Produces a structured pre_analysis dict that is fed to the LLM in prompts.py.
No LLM calls here — purely deterministic scoring using the same column-match
logic already proven in classifier.py.
"""
from __future__ import annotations

import csv
import io
import re
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from containers.implementation.data_readiness_agent.field_policy import (
    assess_field_coverage,
)
from containers.implementation.is_common.party_rules import (
    find_split_column,
    is_customer_role,
    is_supplier_role,
)
from containers.implementation.is_common.required_fields import get_required_fields
from containers.implementation.file_io.manifest_utils import (
    corpus_exclusions_by_doctype,
    normalize_manifest_input,
)

# ─── helpers (replicated from classifier.py to avoid cross-agent imports) ─────

def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", str(s or "").strip().lower())


def _norm_col(s: str) -> str:
    return _norm(str(s or "").replace("_", " "))


def _tokenise(s: str) -> List[str]:
    s = _norm(s)
    return [t for t in re.split(r"[^a-z0-9]+", s) if t]


def _score_columns_vs_doctype(columns: List[str], doctype: str, kb: Dict[str, Any]) -> tuple[float, List[str], List[str]]:
    """
    Score how well a list of file columns covers a doctype's required fields.

    Returns:
        score          — raw weighted match score
        matched_fields — ERPNext fieldnames that were found
        missing_fields — required ERPNext fieldnames NOT found in the file
    """
    dt_cfg = (kb.get("doctypes") or {}).get(doctype) or {}
    fmap = dt_cfg.get("field_mappings") or {}
    mandatory_root = set(dt_cfg.get("mandatory_fields") or [])
    required_fields = [
        fcfg.get("fieldname", fn)
        for fn, fcfg in fmap.items()
        if fcfg.get("mandatory") or fcfg.get("reqd") or fcfg.get("fieldname") in mandatory_root
    ]

    cols = [_norm_col(c) for c in columns if c]
    matched, missing = [], []

    for fn, fcfg in fmap.items():
        erp_name = fcfg.get("fieldname", fn)
        synonyms = [_norm_col(s) for s in (fcfg.get("user_input_synonyms") or [])]
        synonyms.append(_norm_col(erp_name))
        synonyms.append(_norm_col(fn))

        hit = False
        for syn in synonyms:
            if not syn:
                continue
            for col in cols:
                if col == syn or (len(syn) >= 3 and syn in col):
                    hit = True
                    break
            if hit:
                break

        if hit:
            matched.append(erp_name)
        elif erp_name in required_fields:
            missing.append(erp_name)

    graph_required = get_required_fields(doctype)
    for gf in graph_required:
        if gf not in matched and gf not in missing:
            missing.append(gf)

    # Score against graph required fields only (avoids false positives e.g. Stock Entry vs orders)
    graph_matched = [m for m in matched if m in graph_required]
    for gf in graph_required:
        if gf == "items" and any(
            m.startswith("items.") or m in {"item_code", "qty", "rate"}
            for m in matched
        ):
            if gf not in graph_matched:
                graph_matched.append(gf)
    total_fields = max(len(graph_required), 1)
    score = len(graph_matched) / total_fields
    return score, matched, missing


def _keyword_score_text(content: str, doctype: str, kb: Dict[str, Any]) -> float:
    """Score unstructured text vs a doctype using keyword hints."""
    hints = kb.get("doctype_keyword_hints") or {}
    text_l = _norm(content)

    # Shape A: {keyword: doctype}
    if hints and all(isinstance(v, str) for v in hints.values()):
        matches = sum(1 for kw, dt in hints.items() if dt == doctype and _norm(kw) in text_l)
        return min(matches * 0.2, 1.0)

    # Shape B: {doctype: {keywords, min_score}}
    cfg = hints.get(doctype)
    if cfg and isinstance(cfg, dict):
        kws = cfg.get("keywords") or []
        hits = sum(1 for kw in kws if _norm(kw) in text_l)
        min_s = cfg.get("min_score", 3)
        return min(hits / max(min_s, 1), 1.0)

    return 0.0


def _parse_columns_from_content(content: str, filename: str) -> Optional[List[str]]:
    """Extract column headers from CSV/TSV content."""
    try:
        rows = list(csv.DictReader(io.StringIO(content)))
        if rows:
            return [k for k in rows[0].keys() if k]
    except Exception:
        pass
    return None


# ─── MVP scope + evidence helpers ─────────────────────────────────────────────

_ITEM_STUB_COLUMNS = frozenset({"product", "item", "item code", "item_code", "sku", "material", "fg item"})
_TRANSACTIONAL_ORDER_RE = re.compile(
    r"client[_\s-]?order|sales[_\s-]?order|purchase[_\s-]?order|raw[_\s-]?purchase|[_\s-]order",
    re.I,
)


def _resolve_scope_doctypes(target_structure: Dict[str, Any]) -> Tuple[List[str], bool]:
    """Return (doctypes_to_scan, using_mvp_seeds)."""
    deferred = set(target_structure.get("deferred_doctypes") or [])
    seeds = target_structure.get("seed_doctypes") or []
    if seeds:
        return [d for d in seeds if d not in deferred], True
    required = target_structure.get("required_doctypes") or []
    return [d for d in required if d not in deferred], False


def _corpus_doctype_hits(corpus_understanding: Optional[Dict[str, Any]]) -> Dict[str, List[str]]:
    """Map doctype → filenames where corpus understanding positively identified it."""
    hits: Dict[str, List[str]] = {}
    if not corpus_understanding:
        return hits
    for entry in corpus_understanding.get("files") or []:
        if not isinstance(entry, dict):
            continue
        fname = entry.get("filename") or ""
        for dt in entry.get("likely_erpnext_doctypes") or []:
            if fname and dt:
                hits.setdefault(dt, []).append(fname)
    return hits


def _build_party_split_evidence(
    files: Dict[str, str],
    file_meta: Dict[str, Dict],
) -> Dict[str, Dict[str, Any]]:
    """Detect dual-entity party files (Role column → Customer + Supplier)."""
    evidence: Dict[str, Dict[str, Any]] = {}
    for fname, meta in file_meta.items():
        columns = meta.get("columns") or []
        role_col = find_split_column(columns)
        if not role_col:
            continue
        content = files.get(fname) or ""
        if not content:
            continue
        try:
            rows = list(csv.DictReader(io.StringIO(content)))
        except Exception:
            continue
        customer_count = sum(
            1 for r in rows if is_customer_role(r.get(role_col, ""))
        )
        supplier_count = sum(
            1 for r in rows if is_supplier_role(r.get(role_col, ""))
        )
        if customer_count > 0:
            evidence["Customer"] = {
                "source_file": fname,
                "row_count": customer_count,
                "columns": columns,
                "evidence_type": "party_split",
            }
        if supplier_count > 0:
            evidence["Supplier"] = {
                "source_file": fname,
                "row_count": supplier_count,
                "columns": columns,
                "evidence_type": "party_split",
            }
    return evidence


def _build_item_stub_evidence(file_meta: Dict[str, Dict]) -> Dict[str, Any]:
    """Detect Item identity from transactional Product/Item columns."""
    best: Dict[str, Any] = {}
    for fname, meta in file_meta.items():
        columns = meta.get("columns") or []
        cols_norm = {_norm_col(c) for c in columns}
        if not (cols_norm & _ITEM_STUB_COLUMNS):
            continue
        row_count = int(meta.get("row_count") or 0)
        if row_count <= 0 and meta.get("sample_rows"):
            row_count = len(meta["sample_rows"])
        if row_count > 0:
            best = {
                "source_file": fname,
                "row_count": row_count,
                "columns": columns,
                "evidence_type": "transactional_stub",
            }
            break
    return best


def _is_transactional_order_file(fname: str) -> bool:
    return bool(_TRANSACTIONAL_ORDER_RE.search(str(fname or "")))


def _inject_party_scope(
    scope_doctypes: List[str],
    party_evidence: Dict[str, Dict[str, Any]],
) -> List[str]:
    """Ensure Customer/Supplier are assessed when party-split file exists."""
    scope = list(scope_doctypes)
    scope_set = set(scope)
    for dt in party_evidence:
        if dt not in scope_set:
            scope.append(dt)
            scope_set.add(dt)
    return scope


def _filename_prior_boost(fname: str, doctype: str) -> float:
    try:
        from containers.implementation.mapping_agent.corpus_merge import filename_prior_scores
        from containers.implementation.is_common.doctype_resolver import resolve_doctype

        fscores = filename_prior_scores(fname)
        return float(fscores.get(resolve_doctype(doctype), 0.0) or 0.0)
    except Exception:
        return 0.0


def _apply_field_policy(
    doctype: str,
    *,
    matched: List[str],
    missing: List[str],
    columns: List[str],
    kb: Dict[str, Any],
    f3iche_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Classify coverage using graph required_fields (same contract as validate)."""
    return assess_field_coverage(
        doctype, matched, columns, kb, f3iche_id=f3iche_id,
    )


def _run_dry_run(
    doctype: str,
    source_file: str,
    files: Dict[str, str],
    kb: Dict[str, Any],
) -> Dict[str, Any]:
    """Deterministic map→fold→defaults→preflight for readiness gating."""
    content = files.get(source_file) or ""
    if not content:
        return {
            "passed": False,
            "preflight": {
                "blocking": True,
                "missing_fields": [],
                "messages": ["Empty source file"],
            },
            "missing_required_after": [],
            "record_count": 0,
        }
    from containers.implementation.mapping_agent.dry_run_map import dry_run_map_file

    return dry_run_map_file(
        content,
        doctype,
        kb=kb,
        company_context={"company_name": "Session Company"},
    )


def _gate_readiness_entry(
    entry: Dict[str, Any],
    *,
    doctype: str,
    source_file: Optional[str],
    files: Dict[str, str],
    kb: Dict[str, Any],
    policy_can_proceed: bool,
    dry_run_exempt: bool = False,
) -> Tuple[str, Dict[str, Any]]:
    """
    Apply dry-run gating. Returns ('ready'|'partial', entry_with_dry_run_fields).
    """
    out = dict(entry)
    if dry_run_exempt or not source_file:
        out["dry_run_passed"] = True
        out["dry_run_exempt"] = dry_run_exempt
        return ("ready" if policy_can_proceed else "partial", out)

    dry_run = _run_dry_run(doctype, source_file, files, kb)
    out["dry_run"] = dry_run
    out["dry_run_passed"] = bool(dry_run.get("passed"))
    if policy_can_proceed and out["dry_run_passed"]:
        return ("ready", out)

    partial = dict(out)
    partial["dry_run_failed"] = not out["dry_run_passed"]
    partial["missing_required_fields"] = (
        dry_run.get("missing_required_after")
        or out.get("blocking_fields")
        or partial.get("missing_required_fields")
        or []
    )
    partial["can_proceed_without"] = False
    return ("partial", partial)


# ─── public API ───────────────────────────────────────────────────────────────

# Coverage threshold: above this → READY, below → PARTIAL
_READY_THRESHOLD = 0.45
# Minimum graph-field coverage to classify as partial (not missing) when blocking remains
_PARTIAL_THRESHOLD = 0.75
# Minimum score to consider a file as a candidate for a doctype
_CANDIDATE_THRESHOLD = 0.10


def analyze_gaps(
    manifest: Union[Dict[str, str], Dict[str, Any]],
    target_structure: Dict[str, Any],
    field_mappings_kb: Dict[str, Any],
    *,
    f3iche_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Deterministic gap analysis: compare uploaded files against MVP seed doctypes.

    Args:
        manifest:          v2 manifest object OR legacy {filename: content_string}
        target_structure:  ISTargetStructure (seed_doctypes preferred over full graph)
        field_mappings_kb: loaded field_mappings.json

    Returns a pre_analysis dict consumed by the LLM prompt.
    """
    files, prebuilt_meta, corpus_understanding = normalize_manifest_input(manifest)
    doctype_exclusions = corpus_exclusions_by_doctype(corpus_understanding)
    scope_doctypes, mvp_scoped = _resolve_scope_doctypes(target_structure)
    setup_steps: List[Dict] = target_structure.get("setup_steps") or []
    import_phases: Dict[str, Any] = target_structure.get("import_phases") or {}

    # Build doctype → phase and action lookup
    doctype_phase: Dict[str, str] = {}
    doctype_action: Dict[str, str] = {}
    for step in setup_steps:
        dt = step.get("doctype")
        ph = step.get("phase", "unknown")
        act = step.get("action", "must_create")
        if dt:
            doctype_phase[dt] = ph
            doctype_action[dt] = act

    # Build per-file metadata (prefer v2 pre-parsed meta from Step 2)
    file_meta: Dict[str, Dict] = {}
    for fname, content in files.items():
        if not content:
            continue
        pre = prebuilt_meta.get(fname) or {}
        columns = pre.get("columns")
        if not columns:
            is_structured = any(fname.lower().endswith(ext) for ext in (".csv", ".xlsx", ".xls", ".tsv"))
            columns = _parse_columns_from_content(content, fname) if is_structured else None
            is_structured = bool(columns)
        else:
            is_structured = pre.get("is_structured", True)
        file_meta[fname] = {
            "filename": fname,
            "is_structured": is_structured,
            "columns": columns or [],
            "content_snippet": (content or "")[:1500],
            "char_len": pre.get("char_len") or len(content or ""),
            "row_count": pre.get("row_count", 0),
            "sample_rows": pre.get("sample_rows") or [],
        }

    party_evidence = _build_party_split_evidence(files, file_meta)
    scope_doctypes = _inject_party_scope(scope_doctypes, party_evidence)
    item_stub = _build_item_stub_evidence(file_meta)
    corpus_hits = _corpus_doctype_hits(corpus_understanding)

    # ── Classify every scoped doctype ────────────────────────────────────────
    ready_doctypes: List[Dict] = []
    partial_doctypes: List[Dict] = []
    missing_doctypes: List[Dict] = []
    matched_file_doctype_pairs: set = set()

    for doctype in scope_doctypes:
        phase = doctype_phase.get(doctype, "unknown")
        action = doctype_action.get(doctype, "must_create")
        best_score = 0.0
        best_file = None
        best_matched: List[str] = []
        best_missing: List[str] = []
        best_columns: List[str] = []

        # Party-split shortcut (e.g. messy_partners.csv with Role column)
        if doctype in party_evidence:
            pe = party_evidence[doctype]
            identity_field = "customer_name" if doctype == "Customer" else "supplier_name"
            party_matched: List[str] = []
            if any(_norm_col(c) in ("company name", "company_name") for c in pe["columns"]):
                party_matched.append(identity_field)
            policy = _apply_field_policy(
                doctype,
                matched=party_matched,
                missing=[],
                columns=pe["columns"],
                kb=field_mappings_kb,
                f3iche_id=f3iche_id,
            )
            matched_file_doctype_pairs.add((pe["source_file"], doctype))
            entry = {
                "doctype": doctype,
                "source_file": pe["source_file"],
                "coverage_pct": 0.75 if policy["can_proceed_without"] else 0.35,
                "mapped_fields": party_matched,
                "missing_optional_fields": [],
                "assumed_fields": policy["assumed_fields"],
                "blocking_fields": policy["blocking_fields"],
                "ready_with_assumptions": policy["ready_with_assumptions"],
                "can_proceed_without": policy["can_proceed_without"],
                "assumption_only": policy["assumption_only"],
                "phase": phase,
                "evidence_type": "party_split",
            }
            bucket, gated = _gate_readiness_entry(
                entry,
                doctype=doctype,
                source_file=pe["source_file"],
                files=files,
                kb=field_mappings_kb,
                policy_can_proceed=policy["can_proceed_without"],
            )
            if bucket == "ready":
                ready_doctypes.append(gated)
            else:
                partial_doctypes.append(gated)
            continue

        # Transactional Item stub (Product/Item column in orders/POs)
        if doctype == "Item" and item_stub:
            item_matched: List[str] = []
            cols_n = {_norm_col(c) for c in item_stub["columns"]}
            if cols_n & _ITEM_STUB_COLUMNS:
                item_matched.append("item_code")
            policy = _apply_field_policy(
                "Item",
                matched=item_matched,
                missing=[],
                columns=item_stub["columns"],
                kb=field_mappings_kb,
                f3iche_id=f3iche_id,
            )
            matched_file_doctype_pairs.add((item_stub["source_file"], doctype))
            entry = {
                "doctype": doctype,
                "source_file": item_stub["source_file"],
                "coverage_pct": 0.55 if policy["can_proceed_without"] else 0.3,
                "mapped_fields": item_matched,
                "missing_optional_fields": [],
                "assumed_fields": policy["assumed_fields"],
                "blocking_fields": policy["blocking_fields"],
                "ready_with_assumptions": policy["ready_with_assumptions"],
                "can_proceed_without": policy["can_proceed_without"],
                "assumption_only": policy["assumption_only"],
                "phase": phase,
                "evidence_type": "transactional_stub",
            }
            bucket, gated = _gate_readiness_entry(
                entry,
                doctype=doctype,
                source_file=item_stub["source_file"],
                files=files,
                kb=field_mappings_kb,
                policy_can_proceed=policy["can_proceed_without"],
            )
            if bucket == "ready":
                ready_doctypes.append(gated)
            else:
                partial_doctypes.append(gated)
            continue

        for fname, meta in file_meta.items():
            if fname in (doctype_exclusions.get(doctype) or []):
                continue

            if meta["is_structured"] and meta["columns"]:
                score, matched, missing = _score_columns_vs_doctype(
                    meta["columns"], doctype, field_mappings_kb
                )
                best_columns = meta["columns"]
            else:
                score = _keyword_score_text(meta["content_snippet"], doctype, field_mappings_kb)
                matched, missing = [], []

            score += _filename_prior_boost(fname, doctype)

            # Corpus positive signal
            if fname in (corpus_hits.get(doctype) or []):
                score = max(score, 0.5)

            if score > best_score:
                best_score = score
                best_file = fname
                best_matched = matched
                best_missing = missing
                if meta["columns"]:
                    best_columns = meta["columns"]

        # Corpus-only hit (no column match but Step 2b identified doctype)
        corpus_files = corpus_hits.get(doctype) or []
        if not best_file and corpus_files:
            cf = corpus_files[0]
            meta = file_meta.get(cf) or {}
            policy = _apply_field_policy(
                doctype,
                matched=[],
                missing=[],
                columns=meta.get("columns") or [],
                kb=field_mappings_kb,
                f3iche_id=f3iche_id,
            )
            if policy["can_proceed_without"]:
                matched_file_doctype_pairs.add((cf, doctype))
                corpus_entry = {
                    "doctype": doctype,
                    "source_file": cf,
                    "coverage_pct": 0.6,
                    "mapped_fields": [],
                    "missing_optional_fields": [],
                    "assumed_fields": policy["assumed_fields"],
                    "blocking_fields": policy["blocking_fields"],
                    "ready_with_assumptions": True,
                    "can_proceed_without": True,
                    "assumption_only": True,
                    "phase": phase,
                    "evidence_type": "corpus_positive",
                }
                bucket, gated = _gate_readiness_entry(
                    corpus_entry,
                    doctype=doctype,
                    source_file=cf,
                    files=files,
                    kb=field_mappings_kb,
                    policy_can_proceed=True,
                )
                if bucket == "ready":
                    ready_doctypes.append(gated)
                else:
                    partial_doctypes.append(gated)
                continue

        policy = _apply_field_policy(
            doctype,
            matched=best_matched,
            missing=best_missing,
            columns=best_columns,
            kb=field_mappings_kb,
            f3iche_id=f3iche_id,
        )

        if action in ("use_default", "auto_created_by_erpnext"):
            source_file = "System Auto-provisioning" if action == "auto_created_by_erpnext" else "ERPNext Defaults Baseline"
            if best_file:
                source_file = f"{best_file} / {source_file}"
            default_entry = {
                "doctype": doctype,
                "source_file": source_file,
                "coverage_pct": 1.0,
                "mapped_fields": best_matched,
                "missing_optional_fields": [],
                "assumed_fields": policy["assumed_fields"],
                "can_proceed_without": True,
                "phase": phase,
            }
            _, gated = _gate_readiness_entry(
                default_entry,
                doctype=doctype,
                source_file=None,
                files=files,
                kb=field_mappings_kb,
                policy_can_proceed=True,
                dry_run_exempt=True,
            )
            ready_doctypes.append(gated)
        elif policy["can_proceed_without"] and best_file:
            matched_file_doctype_pairs.add((best_file, doctype))
            embedded_project = (
                doctype == "Project"
                and _is_transactional_order_file(best_file)
            )
            ready_entry: Dict[str, Any] = {
                "doctype": doctype,
                "source_file": best_file,
                "coverage_pct": round(max(best_score, 0.5 if policy["ready_with_assumptions"] else best_score), 3),
                "mapped_fields": best_matched,
                "missing_optional_fields": best_missing if not policy["assumption_only"] else [],
                "assumed_fields": policy["assumed_fields"],
                "blocking_fields": policy["blocking_fields"],
                "ready_with_assumptions": policy["ready_with_assumptions"] or embedded_project,
                "can_proceed_without": policy["can_proceed_without"],
                "assumption_only": policy["assumption_only"] or embedded_project,
                "phase": phase,
            }
            if embedded_project:
                ready_entry["evidence_type"] = "embedded_in_transactional"
                ready_entry["coverage_note"] = (
                    "Project names found in order file; no dedicated project master uploaded"
                )
            bucket, gated = _gate_readiness_entry(
                ready_entry,
                doctype=doctype,
                source_file=best_file,
                files=files,
                kb=field_mappings_kb,
                policy_can_proceed=True,
            )
            if bucket == "ready":
                ready_doctypes.append(gated)
            else:
                partial_doctypes.append(gated)
        elif best_score >= _READY_THRESHOLD and best_file and policy["can_proceed_without"]:
            matched_file_doctype_pairs.add((best_file, doctype))
            threshold_entry = {
                "doctype": doctype,
                "source_file": best_file,
                "coverage_pct": round(best_score, 3),
                "mapped_fields": best_matched,
                "missing_optional_fields": best_missing,
                "assumed_fields": policy["assumed_fields"],
                "blocking_fields": policy["blocking_fields"],
                "can_proceed_without": True,
                "phase": phase,
            }
            bucket, gated = _gate_readiness_entry(
                threshold_entry,
                doctype=doctype,
                source_file=best_file,
                files=files,
                kb=field_mappings_kb,
                policy_can_proceed=True,
            )
            if bucket == "ready":
                ready_doctypes.append(gated)
            else:
                partial_doctypes.append(gated)
        elif best_score >= _PARTIAL_THRESHOLD and best_file:
            matched_file_doctype_pairs.add((best_file, doctype))
            partial_doctypes.append({
                "doctype": doctype,
                "source_file": best_file,
                "coverage_pct": round(best_score, 3),
                "missing_required_fields": policy["blocking_fields"] or best_missing,
                "assumed_fields": policy["assumed_fields"],
                "blocking_fields": policy["blocking_fields"],
                "can_proceed_without": policy["can_proceed_without"],
                "assumption_only": policy["assumption_only"],
                "phase": phase,
            })
        else:
            missing_doctypes.append({
                "doctype": doctype,
                "phase": phase,
                "coverage_pct": 0.0,
                "missing_required_fields": policy["blocking_fields"] or best_missing,
                "assumed_fields": policy["assumed_fields"],
                "blocking_fields": policy["blocking_fields"],
                "can_proceed_without": policy["can_proceed_without"],
            })

    kb_doctypes = set((field_mappings_kb.get("doctypes") or {}).keys())

    # ── Corpus expansion: strong filename priors for KB doctypes in scope ──────
    try:
        from containers.implementation.mapping_agent.corpus_merge import filename_implied_doctype
        from containers.implementation.is_common.doctype_resolver import resolve_doctype

        scope_set = set(scope_doctypes)
        seen_ready = {resolve_doctype(r["doctype"]) for r in ready_doctypes}
        seen_partial = {resolve_doctype(p["doctype"]) for p in partial_doctypes}
        for fname in file_meta:
            implied = filename_implied_doctype(fname)
            if not implied:
                continue
            canon = resolve_doctype(implied)
            if canon not in scope_set:
                continue
            if canon in seen_ready or canon in seen_partial:
                continue
            if canon not in kb_doctypes:
                continue
            prior_entry = {
                "doctype": canon,
                "source_file": fname,
                "coverage_pct": 0.85,
                "mapped_fields": [],
                "missing_optional_fields": [],
                "ready_with_assumptions": True,
                "can_proceed_without": True,
                "phase": doctype_phase.get(canon, "phase_c_transactional"),
            }
            bucket, gated = _gate_readiness_entry(
                prior_entry,
                doctype=canon,
                source_file=fname,
                files=files,
                kb=field_mappings_kb,
                policy_can_proceed=True,
            )
            if bucket == "ready":
                ready_doctypes.append(gated)
                seen_ready.add(canon)
            else:
                partial_doctypes.append(gated)
                seen_partial.add(canon)
    except Exception:
        pass

    # ── Unmappable chunks ────────────────────────────────────────────────────
    unmappable_chunks: List[Dict] = []

    for fname, meta in file_meta.items():
        max_any_score = 0.0
        if meta["is_structured"] and meta["columns"]:
            for doctype in kb_doctypes:
                score, _, _ = _score_columns_vs_doctype(meta["columns"], doctype, field_mappings_kb)
                score += _filename_prior_boost(fname, doctype)
                if score > max_any_score:
                    max_any_score = score
        else:
            for doctype in kb_doctypes:
                score = _keyword_score_text(meta["content_snippet"], doctype, field_mappings_kb)
                if score > max_any_score:
                    max_any_score = score

        if max_any_score < _CANDIDATE_THRESHOLD:
            snippet = meta["content_snippet"][:300]
            unmappable_chunks.append({
                "filename": fname,
                "columns": meta["columns"][:20] if meta["columns"] else [],
                "snippet": snippet,
                "max_score_vs_any_doctype": round(max_any_score, 3),
            })

    # ── Summary (MVP seed denominator) ───────────────────────────────────────
    total = len(scope_doctypes)
    n_ready = len(ready_doctypes)
    n_dry_run_ready = sum(1 for r in ready_doctypes if r.get("dry_run_passed"))
    n_assumption_ready = sum(1 for r in ready_doctypes if r.get("ready_with_assumptions"))
    blocking_partial = [p for p in partial_doctypes if not p.get("can_proceed_without")]
    blocking_missing = [m for m in missing_doctypes if not m.get("can_proceed_without")]
    n_field_blocking = sum(
        len(x.get("blocking_fields") or [])
        for x in (*ready_doctypes, *partial_doctypes, *missing_doctypes)
        if not x.get("can_proceed_without")
    )
    raw_score = round(n_dry_run_ready / max(total, 1), 3)

    return {
        "ready_doctypes": ready_doctypes,
        "partial_doctypes": partial_doctypes,
        "missing_doctypes": missing_doctypes,
        "unmappable_chunks": unmappable_chunks,
        "corpus_understanding": corpus_understanding,
        "assumptions": [
            {"doctype": r["doctype"], "fields": r.get("assumed_fields", [])}
            for r in ready_doctypes
            if r.get("assumed_fields")
        ],
        "summary": {
            "total_required": total,
            "mvp_scoped": mvp_scoped,
            "n_ready": n_ready,
            "n_dry_run_ready": n_dry_run_ready,
            "n_assumption_ready": n_assumption_ready,
            "n_partial": len(partial_doctypes),
            "n_blocking_partial": len(blocking_partial),
            "n_missing": len(missing_doctypes),
            "n_blocking_missing": len(blocking_missing),
            "n_field_blocking": n_field_blocking,
            "minimum_viable_possible": len(blocking_missing) == 0 and len(blocking_partial) == 0,
            "n_unmappable_files": len(unmappable_chunks),
            "raw_readiness_score": raw_score,
            "files_scanned": len(file_meta),
        },
    }
