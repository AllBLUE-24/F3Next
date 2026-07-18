"""Tests for mandatory discovery context (Phase 2)."""
from __future__ import annotations

import os

import pytest

from containers.implementation.corpus.discovery_context import (
    DiscoveryContextError,
    build_discovery_context_block,
    require_discovery_context_enabled,
)


def test_build_context_from_metadata():
    result = build_discovery_context_block(
        None,
        {
            "f3iche": "manufacturing_project_chemical",
            "industry": "coatings",
            "mvp_focus": {"primary_bottleneck": "WIP tracking"},
        },
        require=False,
    )
    assert result.ok
    assert "F3iche" in result.context_block
    assert "WIP tracking" in result.context_block


def test_require_raises_without_signal(monkeypatch):
    monkeypatch.setenv("CORPUS_REQUIRE_DISCOVERY", "true")
    monkeypatch.setenv("CORPUS_ALLOW_DEFAULTS", "false")
    with pytest.raises(DiscoveryContextError) as exc:
        build_discovery_context_block(None, None, require=True)
    assert exc.value.code == "DISCOVERY_CONTEXT_MISSING"


def test_allow_defaults_disables_require(monkeypatch):
    monkeypatch.setenv("CORPUS_ALLOW_DEFAULTS", "true")
    assert require_discovery_context_enabled() is False


def test_transcript_alone_satisfies_require():
    result = build_discovery_context_block(
        [{"role": "user", "content": "We run construction project orders from Tally."}],
        None,
        require=True,
    )
    assert result.ok
    assert "construction project orders" in result.context_block
