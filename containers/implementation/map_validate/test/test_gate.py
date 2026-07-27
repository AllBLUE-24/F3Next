"""Gate unit tests."""
from __future__ import annotations

from containers.implementation.map_validate.gate import (
    compute_import_ready,
    compute_validation_level,
)


def test_validation_level_fail():
    assert compute_validation_level({"overall": "fail"}) == "fail"


def test_validation_level_partial_on_warnings():
    assert compute_validation_level({"overall": "pass", "warnings": ["x"]}) == "partial"


def test_import_ready_blocked_on_fail():
    assert compute_import_ready("fail", map_results=[{"passed": True}]) is False
