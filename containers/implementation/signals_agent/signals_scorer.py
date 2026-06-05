"""
Deterministic F3iche scoring from signals_registry.json.

Implements the weighted rule engine described in the registry _meta.how_agent_uses_this:
  scan filenames, column headers, and sample values → score niches → normalize.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_REGISTRY_PATH = (
    Path(__file__).resolve().parent.parent.parent / "knowledge_base" / "common" / "signals_registry.json"
)


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", str(s or "").strip().lower())


def load_signals_registry() -> Dict[str, Any]:
    with open(_REGISTRY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _pattern_matches(text: str, patterns: List[str]) -> Optional[str]:
    text_n = _norm(text)
    for pat in patterns:
        pat_n = _norm(pat)
        if pat_n and pat_n in text_n:
            return pat
    return None


def _column_matches(columns: List[str], patterns: List[str]) -> Optional[str]:
    cols_n = {_norm(c) for c in columns if c}
    for pat in patterns:
        pat_n = _norm(pat)
        if not pat_n:
            continue
        for col in cols_n:
            if col == pat_n or (len(pat_n) >= 3 and pat_n in col):
                return pat
    return None


def _apply_rule(
    scores: Dict[str, float],
    rule: Dict[str, Any],
    *,
    matched_pattern: str,
    found_in: str,
) -> List[Dict[str, Any]]:
    hits: List[Dict[str, Any]] = []
    weight = float(rule.get("weight") or 0.0)
    against_weight = float(rule.get("against_weight") or 0.0)
    signal_type = rule.get("type") or "unknown"

    for niche in rule.get("suggests") or []:
        scores[niche] = scores.get(niche, 0.0) + weight
        hits.append({
            "pattern": matched_pattern,
            "signal_type": signal_type,
            "suggests_f3iche": niche,
            "weight": weight,
            "found_in": found_in,
            "direction": "for",
        })

    for niche in rule.get("against") or []:
        scores[niche] = scores.get(niche, 0.0) - against_weight
        hits.append({
            "pattern": matched_pattern,
            "signal_type": signal_type,
            "suggests_f3iche": niche,
            "weight": -against_weight,
            "found_in": found_in,
            "direction": "against",
        })

    return hits


def _score_structural_rules(
    scores: Dict[str, float],
    rules: List[Dict[str, Any]],
    *,
    file_meta: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    hits: List[Dict[str, Any]] = []
    total_rows = sum(int(m.get("row_count") or 0) for m in file_meta.values())
    unique_item_estimate = 0

    for meta in file_meta.values():
        for row in meta.get("sample_rows") or []:
            for val in row.values():
                if val and re.search(r"[A-Z]{2,}-\w+", str(val)):
                    unique_item_estimate += 1

    for rule in rules:
        pat = _norm(str(rule.get("pattern") or ""))
        if "500 unique" in pat or "500+" in pat:
            if unique_item_estimate >= 5 or total_rows >= 500:
                hits.extend(_apply_rule(scores, rule, matched_pattern=rule.get("pattern", ""), found_in="structural"))
        elif "fewer than 50" in pat or "low item" in pat:
            if total_rows > 0 and total_rows < 50 and unique_item_estimate < 5:
                hits.extend(_apply_rule(scores, rule, matched_pattern=rule.get("pattern", ""), found_in="structural"))

    return hits


def _score_data_value_rules(
    scores: Dict[str, float],
    rules: List[Dict[str, Any]],
    *,
    file_contents: Dict[str, str],
) -> List[Dict[str, Any]]:
    hits: List[Dict[str, Any]] = []
    for fname, content in file_contents.items():
        snippet = (content or "")[:8000]
        for rule in rules:
            if rule.get("type") != "data_pattern":
                continue
            regex = rule.get("regex")
            if regex:
                try:
                    if re.search(regex, snippet, re.MULTILINE | re.IGNORECASE):
                        hits.extend(
                            _apply_rule(scores, rule, matched_pattern=rule.get("pattern", regex), found_in=fname)
                        )
                except re.error:
                    continue
            else:
                pat = str(rule.get("pattern") or "")
                if "size suffix" in pat.lower() and re.search(r"-[SMLX]{1,2}\b", snippet, re.I):
                    hits.extend(_apply_rule(scores, rule, matched_pattern=pat, found_in=fname))
                elif "pipe/grade" in pat.lower() and re.search(r"\d+\s*mm|\d+\s*inch", snippet, re.I):
                    hits.extend(_apply_rule(scores, rule, matched_pattern=pat, found_in=fname))
                elif "part number" in pat.lower() and re.search(r"[A-Z]{2,}-\d{3,}", snippet):
                    hits.extend(_apply_rule(scores, rule, matched_pattern=pat, found_in=fname))

    return hits


def score_manifest(
    *,
    filenames: List[str],
    file_meta: Dict[str, Dict[str, Any]],
    file_contents: Dict[str, str],
    registry: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Score all niches from manifest signals.

    Returns dict with niche_scores (normalized 0-1), hits, top_niche, confidence, margin, signal_count.
    """
    reg = registry or load_signals_registry()
    niche_ids: List[str] = reg.get("_meta", {}).get("niche_ids") or []
    scores: Dict[str, float] = {n: 0.0 for n in niche_ids}
    all_hits: List[Dict[str, Any]] = []

    signal_groups = reg.get("signals") or {}

    # File name rules
    for rule in (signal_groups.get("file_name_signals") or {}).get("rules") or []:
        patterns = rule.get("pattern") or []
        for fname in filenames:
            hit = _pattern_matches(fname, patterns)
            if hit:
                all_hits.extend(_apply_rule(scores, rule, matched_pattern=hit, found_in=fname))

    # Column header rules
    for rule in (signal_groups.get("column_header_signals") or {}).get("rules") or []:
        patterns = rule.get("pattern") or []
        for fname, meta in file_meta.items():
            cols = meta.get("columns") or []
            hit = _column_matches(cols, patterns)
            if hit:
                all_hits.extend(_apply_rule(scores, rule, matched_pattern=hit, found_in=fname))

    # Data value + structural rules
    data_rules = (signal_groups.get("data_value_signals") or {}).get("rules") or []
    all_hits.extend(_score_data_value_rules(scores, data_rules, file_contents=file_contents))
    all_hits.extend(_score_structural_rules(scores, data_rules, file_meta=file_meta))

    # Normalize to 0-1 per niche (clamp negatives to 0)
    max_raw = max(scores.values()) if scores else 0.0
    normalized = {
        n: round(max(0.0, scores[n]) / max_raw, 3) if max_raw > 0 else 0.0
        for n in niche_ids
    }

    ordered = sorted(normalized.items(), key=lambda kv: (-kv[1], kv[0]))
    top_niche = ordered[0][0] if ordered else ""
    top_score = ordered[0][1] if ordered else 0.0
    second_score = ordered[1][1] if len(ordered) > 1 else 0.0
    margin = round(top_score - second_score, 3)

    threshold = float(reg.get("confidence_threshold") or 0.60)
    min_signals = int((reg.get("scoring_logic") or {}).get("minimum_signals_required") or 3)
    signal_count = len(all_hits)

    confident = top_score >= threshold and margin >= 0.05 and signal_count >= min_signals

    return {
        "niche_scores": normalized,
        "raw_scores": scores,
        "hits": all_hits,
        "top_niche": top_niche,
        "confidence": top_score,
        "margin": margin,
        "signal_count": signal_count,
        "confident": confident,
        "threshold": threshold,
    }


def apply_discovery_prior(
    score_result: Dict[str, Any],
    discovery_f3iche: Optional[str],
    *,
    boost: float = 0.15,
) -> Dict[str, Any]:
    """Nudge scores toward discovery f3iche when present (weak prior, not override)."""
    if not discovery_f3iche:
        return score_result

    niche_scores = dict(score_result.get("niche_scores") or {})
    discovery = discovery_f3iche.strip()
    if discovery in niche_scores:
        niche_scores[discovery] = min(1.0, niche_scores[discovery] + boost)
        score_result = dict(score_result)
        score_result["niche_scores"] = niche_scores
        ordered = sorted(niche_scores.items(), key=lambda kv: (-kv[1], kv[0]))
        score_result["top_niche"] = ordered[0][0]
        score_result["confidence"] = ordered[0][1]
        if len(ordered) > 1:
            score_result["margin"] = round(ordered[0][1] - ordered[1][1], 3)
        score_result["discovery_prior_applied"] = discovery
    return score_result


def blend_llm_with_registry(
    *,
    registry_result: Dict[str, Any],
    llm_f3iche: str,
    llm_confidence: float,
) -> Tuple[str, float, str]:
    """
    Combine registry and LLM picks. Returns (f3iche, confidence, method).
    method: registry | llm | blended
    """
    reg_top = registry_result.get("top_niche") or ""
    reg_conf = float(registry_result.get("confidence") or 0.0)
    reg_confident = bool(registry_result.get("confident"))

    if reg_confident and llm_f3iche == reg_top:
        return reg_top, min(1.0, (reg_conf + llm_confidence) / 2 + 0.1), "blended_agree"

    if reg_confident and llm_f3iche != reg_top:
        # Registry wins when confident; note LLM disagreement in signals
        return reg_top, reg_conf, "registry_over_llm"

    if not reg_confident and llm_confidence >= 0.7:
        return llm_f3iche, llm_confidence, "llm"

    if reg_top and reg_conf >= llm_confidence:
        return reg_top, reg_conf, "registry"

    return llm_f3iche or reg_top, max(llm_confidence, reg_conf), "llm_fallback"
