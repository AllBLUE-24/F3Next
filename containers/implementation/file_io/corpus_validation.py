"""Validation helpers for LLM corpus understanding output."""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from containers.implementation.file_io.corpus_models import CorpusUnderstanding, FileUnderstanding

MIN_FILE_CONFIDENCE = 0.45
MIN_REASONING_FOR_EXCLUSION = 1


def validate_corpus_understanding(
    understanding: CorpusUnderstanding,
    expected_filenames: List[str],
) -> Tuple[str, List[Dict[str, str]]]:
    """
    Validate LLM corpus output.

    Returns: (status, warnings) where status is ok | partial | failed
    """
    warnings: List[Dict[str, str]] = []

    if not understanding.files:
        return "failed", [{"code": "EMPTY_OUTPUT", "message": "LLM returned no file understanding entries."}]

    returned = {f.filename for f in understanding.files}
    expected = set(expected_filenames)
    missing = expected - returned
    if missing:
        warnings.append({
            "code": "MISSING_FILES",
            "message": f"Understanding missing for: {', '.join(sorted(missing))}",
        })

    for entry in understanding.files:
        if entry.confidence < MIN_FILE_CONFIDENCE:
            warnings.append({
                "code": "LOW_CONFIDENCE",
                "message": f"{entry.filename}: confidence {entry.confidence:.2f} below {MIN_FILE_CONFIDENCE}",
            })
        if entry.explicitly_not_doctypes and len(entry.reasoning_signals) < MIN_REASONING_FOR_EXCLUSION:
            warnings.append({
                "code": "EXCLUSION_WITHOUT_EVIDENCE",
                "message": (
                    f"{entry.filename}: explicitly_not_doctypes set without reasoning_signals evidence"
                ),
            })
        if not entry.business_description.strip():
            warnings.append({
                "code": "EMPTY_DESCRIPTION",
                "message": f"{entry.filename}: business_description is empty",
            })

    if any(w["code"] == "EMPTY_OUTPUT" for w in warnings):
        return "failed", warnings
    if warnings:
        return "partial", warnings
    return "ok", warnings


def detect_corpus_overclaims(
    matrix: Dict[str, Any],
) -> List[Dict[str, str]]:
    """
    Flag corpus likely_erpnext_doctypes entries with no file column evidence.

    Expects output from assess_file_doctype_matrix (rows + overclaims).
    """
    warnings: List[Dict[str, str]] = []
    for item in matrix.get("overclaims") or []:
        if not isinstance(item, dict):
            continue
        warnings.append({
            "code": "CORPUS_OVERCLAIM",
            "message": item.get("reason") or (
                f"{item.get('filename')}: corpus claimed {item.get('doctype')} without evidence"
            ),
            "filename": str(item.get("filename") or ""),
            "doctype": str(item.get("doctype") or ""),
        })
    return warnings


def validate_corpus_with_matrix(
    understanding: CorpusUnderstanding,
    expected_filenames: List[str],
    matrix: Dict[str, Any],
) -> Tuple[str, List[Dict[str, str]]]:
    """Combine standard corpus validation with matrix-derived overclaim warnings."""
    status, warnings = validate_corpus_understanding(understanding, expected_filenames)
    overclaim_warnings = detect_corpus_overclaims(matrix)
    warnings = list(warnings) + overclaim_warnings
    if overclaim_warnings and status == "ok":
        status = "partial"
    return status, warnings


def merge_missing_file_entries(
    understanding: CorpusUnderstanding,
    expected_filenames: List[str],
) -> CorpusUnderstanding:
    """Add stub entries for files the LLM omitted (keeps pipeline moving)."""
    returned = {f.filename for f in understanding.files}
    files = list(understanding.files)
    for fname in expected_filenames:
        if fname not in returned:
            files.append(FileUnderstanding(
                filename=fname,
                business_description="(auto) File present but not described by corpus LLM",
                confidence=0.3,
                reasoning_signals=["LLM omitted this file — downstream should use deterministic parsing"],
            ))
    return CorpusUnderstanding(corpus_summary=understanding.corpus_summary, files=files)
