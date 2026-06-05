"""Tiered column mapping: KB exact → LLM → KB fuzzy."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from containers.implementation.is_common.required_fields import get_required_fields
from containers.implementation.mapping_agent.column_map_llm import llm_map_columns


def _norm_col(s: str) -> str:
    return re.sub(r"\s+", " ", str(s or "").strip().lower().replace("_", " "))


_GENERIC_FUZZY_TOKENS = frozenset({
    "date", "name", "type", "code", "qty", "rate", "item", "no", "id", "num",
})


def _fuzzy_column_match(col: str, erp_field: str, synonyms: List[str]) -> bool:
    col_n = _norm_col(col)
    tokens = {_norm_col(s) for s in synonyms + [erp_field]}
    for tok in tokens:
        if not tok:
            continue
        if col_n == tok or col_n.replace(" ", "_") == tok.replace(" ", "_"):
            return True
        # Skip generic tokens (e.g. "date" in "target date" → transaction_date)
        if tok in _GENERIC_FUZZY_TOKENS:
            continue
        if len(tok) >= 5 and tok in col_n:
            return True
        if len(col_n) >= 5 and col_n in tok:
            return True
    return False


def kb_fuzzy_map_columns(
    columns: List[str],
    doctype: str,
    kb: Dict[str, Any],
    *,
    already_mapped: Dict[str, str],
) -> Dict[str, str]:
    """Tier 3: token/fuzzy match for columns still unmapped."""
    dt_cfg = (kb.get("doctypes") or {}).get(doctype) or {}
    fmap = dt_cfg.get("field_mappings") or {}
    result = dict(already_mapped)
    mapped_targets = set(result.values())

    for col in columns:
        if col in result:
            continue
        for _fn, cfg in fmap.items():
            erp_name = cfg.get("fieldname", _fn)
            if erp_name in mapped_targets:
                continue
            syns = list(cfg.get("user_input_synonyms") or [])
            if _fuzzy_column_match(col, erp_name, syns):
                result[col] = erp_name
                mapped_targets.add(erp_name)
                break
    return result


async def map_columns_tiered(
    engine,
    columns: List[str],
    doctype: str,
    *,
    sample_rows: Optional[List[Dict[str, Any]]] = None,
    corpus_hints: Optional[Dict[str, Any]] = None,
    kb: Optional[Dict[str, Any]] = None,
) -> Tuple[Dict[str, str], Dict[str, Any]]:
    """
    Tier 1 KB exact → Tier 2 LLM → Tier 3 KB fuzzy.

    Returns (field_mapping, audit_meta).
    """
    if not doctype or not columns:
        return {}, {"methods": {}}

    kb = kb or engine._load_field_mappings()
    samples = sample_rows or []

    # Tier 1
    tier1 = engine.map_columns(columns, doctype, sample_row=samples[0] if samples else None)
    audit: Dict[str, Any] = {"methods": {src: "kb_local" for src in tier1}}

    unmapped = [c for c in columns if c not in tier1]
    required = get_required_fields(doctype)
    mapped_targets = set(tier1.values())
    missing_required = [f for f in required if f not in mapped_targets]

    # Tier 2 — LLM for unmapped cols or required fields still without a source column
    llm_cols = list(unmapped)
    if missing_required:
        llm_cols = list(dict.fromkeys(llm_cols + columns))  # re-evaluate all if required gaps

    tier2: Dict[str, str] = {}
    if llm_cols and (unmapped or missing_required):
        tier2 = await llm_map_columns(
            doctype=doctype,
            columns=columns,
            sample_rows=samples,
            required_fields=missing_required or required,
            unmapped_columns=unmapped or columns,
            kb=kb,
            corpus_hints=corpus_hints,
        )
        for src, tgt in tier2.items():
            if src not in tier1:
                audit["methods"][src] = "llm_column_map"

    merged = {**tier1, **{k: v for k, v in tier2.items() if k not in tier1}}

    # Tier 3 fuzzy for anything still unmapped
    before_fuzzy = set(merged.keys())
    merged = kb_fuzzy_map_columns(columns, doctype, kb, already_mapped=merged)
    for src in merged:
        if src not in before_fuzzy and audit["methods"].get(src) != "llm_column_map":
            audit["methods"][src] = "kb_fuzzy"

    audit["unmapped_after"] = [c for c in columns if c not in merged]
    audit["required_fields"] = required
    audit["missing_required_after"] = [
        f for f in required if f not in set(merged.values())
    ]
    return merged, audit
