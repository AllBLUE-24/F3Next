"""Readiness models smoke tests."""
from __future__ import annotations

from containers.implementation.readiness.models import MatrixRow, ReadinessReport


def test_readiness_report_defaults():
    report = ReadinessReport()
    assert report.readiness_level == "yellow"
    assert report.matrix.rows == []


def test_matrix_row_status():
    row = MatrixRow(filename="a.csv", doctype="Item", status="ready")
    assert row.status == "ready"
