"""Tests for department taxonomy."""

from shared.erp_policies.departments import Department


def test_department_normalize_valid():
    assert Department.normalize("Sales") == "sales"
    assert Department.normalize("PURCHASE") == "purchase"


def test_department_normalize_invalid():
    assert Department.normalize("") is None
    assert Department.normalize("engineering") is None


def test_department_values():
    assert "sales" in Department.values()
    assert "admin" in Department.values()
