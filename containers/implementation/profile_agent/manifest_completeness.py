"""Deterministic manifest completeness score for profile enrichment."""
from __future__ import annotations

from typing import Any, Dict, Optional


def score_manifest_completeness(
    manifest: Optional[Dict[str, Any]],
    *,
    draft_doctype_count: int = 0,
) -> float:
    """
    Score 0–1 how much of an implementation-ready dataset is present in the upload.

    Uses file count, structured ratio, and row volume — not LLM opinion.
    """
    if not manifest:
        return 0.0

    file_meta: Dict[str, Dict[str, Any]] = manifest.get("file_meta") or {}
    files = manifest.get("files") or {}
    if not file_meta and not files:
        return 0.0

    names = list(file_meta.keys()) or list(files.keys())
    file_count = len(names)
    if file_count == 0:
        return 0.0

    structured = sum(1 for m in file_meta.values() if m.get("is_structured"))
    total_rows = sum(int(m.get("row_count") or 0) for m in file_meta.values())
    structured_ratio = structured / file_count if file_count else 0.0

    # Small uploads (3 CSVs, few rows) should not score high for a 15-doctype niche
    file_factor = min(1.0, file_count / 8.0)
    row_factor = min(1.0, total_rows / 50.0)
    doctype_factor = 1.0
    if draft_doctype_count > 0:
        doctype_factor = min(1.0, file_count / max(3, draft_doctype_count * 0.25))

    score = (
        file_factor * 0.35
        + row_factor * 0.25
        + structured_ratio * 0.25
        + doctype_factor * 0.15
    )
    return round(min(1.0, max(0.0, score)), 2)
