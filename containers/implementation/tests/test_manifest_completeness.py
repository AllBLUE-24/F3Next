"""Tests for deterministic manifest completeness scoring."""
from __future__ import annotations

from containers.implementation.profile_agent.manifest_completeness import score_manifest_completeness


def test_empty_manifest_scores_zero():
    assert score_manifest_completeness(None) == 0.0
    assert score_manifest_completeness({}) == 0.0


def test_small_upload_scores_moderate():
    manifest = {
        "file_meta": {
            "orders.csv": {"is_structured": True, "row_count": 2},
            "partners.csv": {"is_structured": True, "row_count": 3},
            "po.csv": {"is_structured": True, "row_count": 4},
        },
        "files": {"orders.csv": "...", "partners.csv": "...", "po.csv": "..."},
    }
    score = score_manifest_completeness(manifest, draft_doctype_count=15)
    assert 0.2 < score < 0.6


def test_larger_upload_scores_higher():
    manifest = {
        "file_meta": {
            f"f{i}.csv": {"is_structured": True, "row_count": 20}
            for i in range(8)
        },
        "files": {f"f{i}.csv": "data" for i in range(8)},
    }
    score = score_manifest_completeness(manifest, draft_doctype_count=5)
    assert score >= 0.7
