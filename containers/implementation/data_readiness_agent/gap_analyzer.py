"""
data_readiness_agent/gap_analyzer.py

Deterministic pre-LLM gap analysis.

Given:
  - manifest: {filename: content_or_columns} from R2
  - target_structure: ISTargetStructure result (required_doctypes, setup_steps, import_phases)
  - field_mappings_kb: the field_mappings.json knowledge base

Produces a structured pre_analysis dict that is fed to the LLM in prompts.py.
No LLM calls here — purely deterministic scoring using the same column-match
logic already proven in classifier.py.
"""
from __future__ import annotations

import csv
import io
import re
from typing import Any, Dict, List, Optional

# ─── helpers (replicated from classifier.py to avoid cross-agent imports) ─────

def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", str(s or "").strip().lower())


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
    required_fields = [
        fcfg.get("fieldname", fn)
        for fn, fcfg in fmap.items()
        if fcfg.get("reqd") or fcfg.get("in_list_view")
    ]

    cols = [_norm(c) for c in columns if c]
    matched, missing = [], []

    for fn, fcfg in fmap.items():
        erp_name = fcfg.get("fieldname", fn)
        synonyms = [_norm(s) for s in (fcfg.get("user_input_synonyms") or [])]
        synonyms.append(_norm(erp_name))
        synonyms.append(_norm(fn))

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

    total_fields = max(len(fmap), 1)
    score = len(matched) / total_fields
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


# ─── public API ───────────────────────────────────────────────────────────────

# Coverage threshold: above this → READY, below → PARTIAL
_READY_THRESHOLD = 0.45
# Minimum score to consider a file as a candidate for a doctype
_CANDIDATE_THRESHOLD = 0.10


def analyze_gaps(
    manifest: Dict[str, str],
    target_structure: Dict[str, Any],
    field_mappings_kb: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Deterministic gap analysis: compare every uploaded file against every
    required doctype and classify coverage.

    Args:
        manifest:          {filename: file_content_string}
        target_structure:  ISTargetStructure.primary_result["target_structure"]
                           (has required_doctypes, setup_steps, import_phases)
        field_mappings_kb: loaded field_mappings.json

    Returns a pre_analysis dict consumed by the LLM prompt.
    """
    required_doctypes: List[str] = target_structure.get("required_doctypes") or []
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

    # Pre-parse all files
    file_meta: Dict[str, Dict] = {}
    for fname, content in manifest.items():
        if not content:
            continue
        is_structured = any(fname.lower().endswith(ext) for ext in (".csv", ".xlsx", ".xls", ".tsv"))
        columns = _parse_columns_from_content(content, fname) if is_structured else None
        file_meta[fname] = {
            "filename": fname,
            "is_structured": is_structured,
            "columns": columns or [],
            "content_snippet": (content or "")[:1500],
            "char_len": len(content or ""),
        }

    # ── Classify every required doctype ──────────────────────────────────────
    ready_doctypes: List[Dict] = []
    partial_doctypes: List[Dict] = []
    missing_doctypes: List[Dict] = []
    matched_file_doctype_pairs: set = set()   # (filename, doctype) that scored

    for doctype in required_doctypes:
        phase = doctype_phase.get(doctype, "unknown")
        action = doctype_action.get(doctype, "must_create")
        best_score = 0.0
        best_file = None
        best_matched: List[str] = []
        best_missing: List[str] = []

        for fname, meta in file_meta.items():
            if meta["is_structured"] and meta["columns"]:
                score, matched, missing = _score_columns_vs_doctype(
                    meta["columns"], doctype, field_mappings_kb
                )
            else:
                score = _keyword_score_text(meta["content_snippet"], doctype, field_mappings_kb)
                matched, missing = [], []

            if score > best_score:
                best_score = score
                best_file = fname
                best_matched = matched
                best_missing = missing

        if best_score >= _READY_THRESHOLD and best_file:
            matched_file_doctype_pairs.add((best_file, doctype))
            ready_doctypes.append({
                "doctype": doctype,
                "source_file": best_file,
                "coverage_pct": round(best_score, 3),
                "mapped_fields": best_matched,
                "missing_optional_fields": best_missing,
                "phase": phase,
            })
        elif action in ("use_default", "auto_created_by_erpnext"):
            # Automatically ready via system defaults or auto-provisioning
            source_file = "System Auto-provisioning" if action == "auto_created_by_erpnext" else "ERPNext Defaults Baseline"
            if best_file:
                source_file = f"{best_file} / {source_file}"
            ready_doctypes.append({
                "doctype": doctype,
                "source_file": source_file,
                "coverage_pct": 1.0,
                "mapped_fields": best_matched,
                "missing_optional_fields": [],
                "phase": phase,
            })
        elif best_score >= _CANDIDATE_THRESHOLD and best_file:
            matched_file_doctype_pairs.add((best_file, doctype))
            partial_doctypes.append({
                "doctype": doctype,
                "source_file": best_file,
                "coverage_pct": round(best_score, 3),
                "missing_required_fields": best_missing,
                "phase": phase,
            })
        else:
            missing_doctypes.append({
                "doctype": doctype,
                "phase": phase,
                "coverage_pct": 0.0,
                "missing_required_fields": best_missing,
            })

    # ── Unmappable chunks: file portions not matched to anything ─────────────
    unmappable_chunks: List[Dict] = []
    kb_doctypes = set((field_mappings_kb.get("doctypes") or {}).keys())

    for fname, meta in file_meta.items():
        # Check if this file scored meaningfully for ANY known doctype
        max_any_score = 0.0
        if meta["is_structured"] and meta["columns"]:
            for doctype in kb_doctypes:
                score, _, _ = _score_columns_vs_doctype(meta["columns"], doctype, field_mappings_kb)
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

    # ── Summary ───────────────────────────────────────────────────────────────
    total = len(required_doctypes)
    n_ready = len(ready_doctypes)
    raw_score = round(n_ready / max(total, 1), 3)

    return {
        "ready_doctypes": ready_doctypes,
        "partial_doctypes": partial_doctypes,
        "missing_doctypes": missing_doctypes,
        "unmappable_chunks": unmappable_chunks,
        "summary": {
            "total_required": total,
            "n_ready": n_ready,
            "n_partial": len(partial_doctypes),
            "n_missing": len(missing_doctypes),
            "n_unmappable_files": len(unmappable_chunks),
            "raw_readiness_score": raw_score,
            "files_scanned": len(file_meta),
        },
    }
