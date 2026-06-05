"""Tests for shared required-fields contract."""
from __future__ import annotations

from containers.implementation.is_common.required_fields import (
    get_required_fields,
    normalize_required_fieldnames,
)


def test_normalize_strips_parenthetical():
    assert normalize_required_fieldnames(["items (item_code, qty, rate)"]) == ["items"]


def test_sales_order_includes_delivery_date_from_graph():
    fields = get_required_fields("Sales Order")
    assert "customer" in fields
    assert "delivery_date" in fields


def test_purchase_order_includes_supplier():
    fields = get_required_fields("Purchase Order")
    assert "supplier" in fields
