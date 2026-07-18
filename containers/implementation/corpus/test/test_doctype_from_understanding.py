"""Tests for corpus-first doctype assignment (Phase 4)."""
from __future__ import annotations

import os

import pytest

from containers.implementation.corpus.doctype_from_understanding import (
    assignment_from_corpus_understanding,
    use_legacy_corpus_classifier,
)


CORPUS = {
    "files": [
        {
            "filename": "client_orders.csv",
            "likely_erpnext_doctypes": ["Sales Order", "Customer"],
            "explicitly_not_doctypes": ["Work Order"],
            "confidence": 0.85,
            "reasoning_signals": ["project order columns"],
        }
    ]
}


def test_assignment_from_corpus_when_flag_off(monkeypatch):
    monkeypatch.setenv("CORPUS_USE_LEGACY_CLASSIFIER", "false")
    assert use_legacy_corpus_classifier() is False
    result = assignment_from_corpus_understanding(
        "client_orders.csv",
        CORPUS,
        ["Sales Order", "Customer", "Work Order"],
    )
    assert result is not None
    assert result["doctypes"] == ["Sales Order", "Customer"]
    assert result["classification"]["method"] == "corpus_understanding"


def test_skips_legacy_when_flag_on(monkeypatch):
    monkeypatch.setenv("CORPUS_USE_LEGACY_CLASSIFIER", "true")
    assert assignment_from_corpus_understanding("client_orders.csv", CORPUS, ["Sales Order"]) is None


def test_skips_low_confidence(monkeypatch):
    monkeypatch.setenv("CORPUS_USE_LEGACY_CLASSIFIER", "false")
    low = {
        "files": [{
            "filename": "a.csv",
            "likely_erpnext_doctypes": ["Item"],
            "confidence": 0.2,
        }]
    }
    assert assignment_from_corpus_understanding("a.csv", low, ["Item"]) is None
