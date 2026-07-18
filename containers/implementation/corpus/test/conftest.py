"""Pytest config for Step 2 corpus tests."""

from __future__ import annotations

import pytest


def pytest_configure(config):
    config.addinivalue_line("markers", "golden: Step 2 corpus golden gate tests")
    config.addinivalue_line("markers", "live_llm: Requires live LLM credentials")
