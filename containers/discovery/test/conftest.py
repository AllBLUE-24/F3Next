"""Pytest config for discovery tests."""

from __future__ import annotations

import os

import pytest


@pytest.fixture(autouse=True)
def _discovery_golden_env(request, monkeypatch):
    """Force core-only path for golden MVP boundary tests."""
    if request.node.get_closest_marker("golden"):
        monkeypatch.setenv("DISCOVERY_USE_MVP_MAP_FALLBACK", "false")
        monkeypatch.setenv("DISCOVERY_USE_LEGACY_REGEX_SCOPING", "false")
        monkeypatch.setenv("DISCOVERY_USE_F3ICHE_BOTTLENECKS", "true")


def pytest_configure(config):
    config.addinivalue_line("markers", "golden: Discovery MVP boundary golden gate tests")
    config.addinivalue_line("markers", "live_llm: Requires live LLM credentials")
    config.addinivalue_line("markers", "routing_matrix: Live routing matrix deterministic checks")
