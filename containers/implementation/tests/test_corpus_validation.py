"""Tests for corpus understanding validation."""
from __future__ import annotations

from containers.implementation.file_io.corpus_models import CorpusUnderstanding, FileUnderstanding
from containers.implementation.file_io.corpus_validation import validate_corpus_understanding


def test_validate_ok_when_complete():
    understanding = CorpusUnderstanding(
        corpus_summary="Procurement and client orders.",
        files=[
            FileUnderstanding(
                filename="a.csv",
                business_description="Purchase orders",
                likely_erpnext_doctypes=["Purchase Order"],
                confidence=0.8,
                reasoning_signals=["PO_Number column with vendor and item rows"],
            )
        ],
    )
    status, warnings = validate_corpus_understanding(understanding, ["a.csv"])
    assert status == "ok"
    assert not warnings


def test_validate_partial_on_low_confidence():
    understanding = CorpusUnderstanding(
        corpus_summary="Unclear",
        files=[
            FileUnderstanding(
                filename="a.csv",
                business_description="Maybe orders",
                confidence=0.2,
            )
        ],
    )
    status, warnings = validate_corpus_understanding(understanding, ["a.csv"])
    assert status == "partial"
    assert any(w["code"] == "LOW_CONFIDENCE" for w in warnings)


def test_validate_partial_on_exclusion_without_evidence():
    understanding = CorpusUnderstanding(
        corpus_summary="Orders",
        files=[
            FileUnderstanding(
                filename="a.csv",
                business_description="Client orders",
                explicitly_not_doctypes=["Work Order"],
                confidence=0.8,
                reasoning_signals=[],
            )
        ],
    )
    status, warnings = validate_corpus_understanding(understanding, ["a.csv"])
    assert status == "partial"
    assert any(w["code"] == "EXCLUSION_WITHOUT_EVIDENCE" for w in warnings)
