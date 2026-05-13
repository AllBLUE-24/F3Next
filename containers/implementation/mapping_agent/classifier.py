"""
Deterministic DocType classification (Step A) for Mapping Agent.

Design:
- Use bounded candidate list (session-scoped) to reduce confusion.
- Prefer deterministic local scoring; call LLM only when ambiguous.
- Guarantee a doctype is returned (never drop a file due to "no match").
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field, create_model
from typing import Literal

from containers.implementation.mapping_agent.kb import field_mappings as _field_mappings
from shared.structured_llm import generate_typed


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", str(s or "").strip().lower())


def _tokenise(s: str) -> List[str]:
    s = _norm(s)
    return [t for t in re.split(r"[^a-z0-9]+", s) if t]


def _score_by_columns(doctype: str, columns: List[str], kb: Dict[str, Any]) -> float:
    dt_cfg = (kb.get("doctypes") or {}).get(doctype) or {}
    fmap = dt_cfg.get("field_mappings") or {}
    cols = [_norm(c) for c in columns if c]
    if not cols:
        return 0.0

    score = 0.0
    for _, fcfg in fmap.items():
        synonyms = list(fcfg.get("user_input_synonyms") or [])
        synonyms.append(fcfg.get("fieldname") or "")
        synonyms = [_norm(x) for x in synonyms if x]
        for syn in synonyms:
            for c in cols:
                if c == syn:
                    score += 3.0
                    break
                if syn and syn in c and len(syn) >= 3:
                    score += 1.5
                    break
    return score


def _keyword_hints_score(text: str, filename: str, candidates: List[str], kb: Dict[str, Any]) -> Dict[str, float]:
    """
    Supports BOTH shapes:
    - {keyword: Doctype}   (current KB)
    - {Doctype: {keywords:[...], min_score:N}}  (future-proof)
    """
    text_l = _norm(text)
    fname_l = _norm(filename)
    hints = kb.get("doctype_keyword_hints") or {}
    scores: Dict[str, float] = {c: 0.0 for c in candidates}

    # Shape A: keyword -> doctype
    if hints and all(isinstance(k, str) and isinstance(v, str) for k, v in hints.items()):
        for kw, dt in hints.items():
            if dt not in scores:
                continue
            kw_l = _norm(kw)
            if not kw_l:
                continue
            if kw_l in text_l:
                scores[dt] += 1.0
            if kw_l in fname_l:
                scores[dt] += 0.7
        return scores

    # Shape B: doctype -> {keywords, min_score}
    if hints and all(isinstance(v, dict) for v in hints.values()):
        for dt, cfg in hints.items():
            if dt not in scores:
                continue
            kws = cfg.get("keywords") or []
            for kw in kws:
                kw_l = _norm(kw)
                if kw_l and kw_l in text_l:
                    scores[dt] += 1.0
        return scores

    return scores


def _filename_priors(filename: str, candidates: List[str]) -> Dict[str, float]:
    f = _norm(filename)
    scores: Dict[str, float] = {c: 0.0 for c in candidates}
    # Strong priors from common abbreviations / keywords
    priors: List[Tuple[str, str, float]] = [
        ("so", "Sales Order", 1.5),
        ("sales order", "Sales Order", 2.0),
        ("po", "Purchase Order", 1.5),
        ("purchase order", "Purchase Order", 2.0),
        ("item", "Item", 1.0),
        ("customer", "Customer", 1.0),
        ("supplier", "Supplier", 1.0),
        ("vendor", "Supplier", 0.7),
        ("invoice", "Sales Invoice", 0.7),
        ("purchase invoice", "Purchase Invoice", 1.2),
    ]
    for kw, dt, w in priors:
        if dt in scores and kw in f:
            scores[dt] += w
    return scores


def _local_classify(
    *,
    filename: str,
    content_snippet: str,
    columns: Optional[List[str]],
    candidates: List[str],
) -> Tuple[str, Dict[str, float]]:
    kb = _field_mappings() or {}

    scores: Dict[str, float] = {c: 0.0 for c in candidates}

    # Column-based scoring (structured files)
    if columns:
        for c in candidates:
            scores[c] += _score_by_columns(c, columns, kb)

    # Keyword hints scoring (unstructured)
    kw_scores = _keyword_hints_score(content_snippet, filename, candidates, kb)
    for c, v in kw_scores.items():
        scores[c] += v

    # Filename priors
    fpri = _filename_priors(filename, candidates)
    for c, v in fpri.items():
        scores[c] += v

    # Deterministic pick
    best = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0].lower()))[0][0] if scores else (candidates[0] if candidates else "")
    return best, scores


async def classify_doctype(
    *,
    filename: str,
    content_snippet: str,
    columns: Optional[List[str]],
    candidates: List[str],
    model_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Returns: {doctype, confidence, method, scores, signals}
    Always returns a doctype from candidates (if candidates non-empty).
    """
    if not candidates:
        return {"doctype": None, "confidence": 0.0, "method": "none", "scores": {}, "signals": ["no_candidates"]}

    best, scores = _local_classify(
        filename=filename,
        content_snippet=content_snippet or "",
        columns=columns,
        candidates=candidates,
    )

    ordered = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0].lower()))
    top_score = ordered[0][1] if ordered else 0.0
    second = ordered[1][1] if len(ordered) > 1 else 0.0
    margin = top_score - second

    # If local routing is confident enough, skip LLM.
    if top_score >= 4.0 and margin >= 1.5:
        return {
            "doctype": best,
            "confidence": 0.90,
            "method": "local",
            "scores": scores,
            "signals": ["local_high_confidence"],
        }

    # LLM fallback — classification ONLY
    candidates_with_escape = list(candidates) + ["Unmapped_Irrelevant"]
    DoctypeLiteral = Literal.__getitem__(tuple(candidates_with_escape))
    ClassificationSchema = create_model(  # type: ignore[misc]
        "DocTypeClassification",
        __config__=ConfigDict(extra="forbid"),
        doctype=(DoctypeLiteral, ...),
        confidence=(float, Field(ge=0.0, le=1.0)),
        signals=(List[str], Field(default_factory=list)),
    )

    snippet = (content_snippet or "")[:1200]
    prompt = (
        "You are an ERPNext doctype classifier.\n"
        "Task: pick the SINGLE best matching doctype from the provided candidate list.\n"
        "Do NOT extract any data. Do NOT invent doctypes.\n\n"
        f"Filename: {filename}\n"
    )
    if columns:
        prompt += f"Columns: {columns[:60]}\n"
    prompt += f"\nContent snippet:\n{snippet}\n\nCandidate doctypes:\n{candidates_with_escape}\n\nReturn strictly the JSON schema."

    try:
        res = await generate_typed(
            prompt=prompt,
            schema=ClassificationSchema,  # type: ignore[arg-type]
            model_name=model_name or "gpt-4o-mini",
            temperature=0.0,
            max_output_tokens=600,
            system_instruction="Return only the JSON object. No markdown.",
        )
        chosen = res.get("doctype") or best
        if chosen not in candidates_with_escape:
            chosen = best
        conf = float(res.get("confidence") or 0.6)
        return {
            "doctype": chosen,
            "confidence": max(0.55, min(conf, 1.0)),
            "method": "llm",
            "scores": scores,
            "signals": ["llm_fallback"] + list(res.get("signals") or []),
        }
    except Exception as e:
        # Deterministic fallback: local best
        return {
            "doctype": best,
            "confidence": 0.55,
            "method": "local_fallback",
            "scores": scores,
            "signals": ["llm_failed", str(e)[:120]],
        }

