"""Unit tests for Step 2 gate checkers."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from containers.implementation.corpus.checkers import (
    check_manifest_v2_shape,
    evaluate_step2_gate,
)
from containers.implementation.corpus.manifest import build_manifest_v2

FIXTURES = Path(__file__).parent / "fixtures"


def test_check_manifest_v2_shape_ok():
    manifest = build_manifest_v2({"a.csv": "x,y\n1,2"}, created_at="2026-01-01T00:00:00Z")
    issues = check_manifest_v2_shape(manifest)
    assert not any(i.severity == "error" for i in issues)


def test_check_manifest_v2_shape_rejects_empty():
    issues = check_manifest_v2_shape({})
    assert any(i.code == "EMPTY_MANIFEST" for i in issues)


@pytest.mark.golden
def test_green_surface_fixture_passes_gate():
    raw = json.loads((FIXTURES / "green_surface_manifest.json").read_text(encoding="utf-8"))
    golden = raw.pop("_golden", {})
    result = evaluate_step2_gate(
        raw,
        file_doctype_expectations=golden.get("file_doctype_expectations"),
        file_exclusion_expectations=golden.get("file_exclusion_expectations"),
    )
    assert result.manifest_ok
    assert result.understanding_ok
    assert result.passed
    assert result.status in ("ok", "partial")


def test_gate_fails_without_corpus_understanding():
    manifest = build_manifest_v2({"a.csv": "x,y\n1,2"}, created_at="2026-01-01T00:00:00Z")
    result = evaluate_step2_gate(manifest, require_understanding=True)
    assert not result.passed
    assert result.status == "failed"
    assert any(i.code == "NO_CORPUS_UNDERSTANDING" for i in result.issues)
