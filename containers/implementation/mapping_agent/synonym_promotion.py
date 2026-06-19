"""Suggest KB synonym promotions from dry-run / mapping gaps."""
from __future__ import annotations

from typing import Any, Dict, List


def suggest_synonym_promotions(
    *,
    doctype: str,
    field_mapping: Dict[str, str],
    columns: List[str],
    missing_required: List[str],
    unmapped_columns: List[str] | None = None,
) -> List[Dict[str, Any]]:
    """
    Golden-failure → KB checklist rows for manual promotion to mapping/*.json.

    Returns list of {doctype, erp_field, source_column, reason}.
    """
    suggestions: List[Dict[str, Any]] = []
    mapped_sources = set(field_mapping.keys())
    unmapped = list(unmapped_columns or [c for c in columns if c not in mapped_sources])

    for col in unmapped:
        suggestions.append({
            "doctype": doctype,
            "erp_field": None,
            "source_column": col,
            "reason": "unmapped_column",
            "kb_action": f"Add '{col}' to user_input_synonyms for the matching ERP field",
        })

    mapped_targets = set(field_mapping.values())
    for req in missing_required or []:
        if req in mapped_targets or any(t.endswith(f".{req}") for t in mapped_targets):
            continue
        suggestions.append({
            "doctype": doctype,
            "erp_field": req,
            "source_column": None,
            "reason": "missing_required_after_map",
            "kb_action": f"Add column synonyms for required field '{req}' in {doctype}.json",
        })

    return suggestions


def build_promotion_report(
    *,
    successful_learnings: List[Dict[str, Any]],
    gap_suggestions: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Combined KB promotion checklist for golden/beta runs."""
    return {
        "successful_learnings": successful_learnings,
        "gap_suggestions": gap_suggestions,
        "total_items": len(successful_learnings) + len(gap_suggestions),
    }
