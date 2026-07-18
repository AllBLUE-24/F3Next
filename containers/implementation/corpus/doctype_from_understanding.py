"""Assign ERPNext doctypes from Step 2 corpus understanding (no patch KB priors)."""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from containers.implementation.corpus.manifest import corpus_file_understanding
from containers.implementation.corpus.validation import MIN_FILE_CONFIDENCE


def use_legacy_corpus_classifier() -> bool:
    return os.getenv("CORPUS_USE_LEGACY_CLASSIFIER", "false").lower() in ("true", "1", "yes")


def assignment_from_corpus_understanding(
    filename: str,
    corpus_understanding: Optional[Dict[str, Any]],
    candidates: List[str],
) -> Optional[Dict[str, Any]]:
    """
    When corpus understanding is authoritative, return a corpus assignment dict.

    Skipped when CORPUS_USE_LEGACY_CLASSIFIER=true (Phase 4 default: false).
    """
    if use_legacy_corpus_classifier():
        return None

    entry = corpus_file_understanding(corpus_understanding, filename)
    if not entry:
        return None

    confidence = float(entry.get("confidence") or 0)
    if confidence < MIN_FILE_CONFIDENCE:
        return None

    raw_doctypes = list(entry.get("likely_erpnext_doctypes") or [])
    if not raw_doctypes:
        return None

    excluded = set(entry.get("explicitly_not_doctypes") or [])
    picked = [d for d in raw_doctypes if d in candidates and d not in excluded]
    if not picked:
        return None

    primary = picked[0]
    return {
        "file": filename,
        "doctypes": picked,
        "classification": {
            "doctype": primary,
            "method": "corpus_understanding",
            "confidence": confidence,
            "signals": list(entry.get("reasoning_signals") or []),
            "corpus_summary": (entry.get("business_description") or "")[:200],
        },
    }
