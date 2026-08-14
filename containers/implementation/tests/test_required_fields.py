"""Tests for shared required-fields contract."""
from __future__ import annotations

from containers.implementation.is_common.required_fields import (
    get_required_fields,
    normalize_required_fieldnames,
    resolve_required_fields,
)
from containers.implementation.validation_agent.activities import _ValidationEngine


def test_normalize_strips_parenthetical():
    assert normalize_required_fieldnames(["items (item_code, qty, rate)"]) == ["items"]


def test_sales_order_includes_delivery_date_from_graph():
    fields = get_required_fields("Sales Order")
    assert "customer" in fields
    assert "delivery_date" in fields


def test_purchase_order_includes_supplier():
    fields = get_required_fields("Purchase Order")
    assert "supplier" in fields


def test_validation_uses_shared_required_field_resolver():
    graph = {
        "doctypes": {
            "Custom Document": {
                "required_fields": ["parent (child)", "paid_to/paid_from"],
            },
        },
    }
    expected = resolve_required_fields(
        "Custom Document",
        graph=graph,
        kb_rules={},
    )
    engine = _ValidationEngine(graph=graph, field_mappings={})
    assert engine._get_required_fields("Custom Document") == expected
