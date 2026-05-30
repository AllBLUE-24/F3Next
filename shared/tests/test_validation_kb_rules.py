"""Validation engine KB rules."""

from containers.implementation.validation_agent.activities import _ValidationEngine


def test_kb_required_fields_for_bom():
    engine = _ValidationEngine(graph={}, field_mappings={})
    fields = engine._get_required_fields("BOM")
    assert "item" in fields
    assert "company" in fields


def test_kb_message_for_missing_field():
    engine = _ValidationEngine(graph={}, field_mappings={})
    msg = engine._format_kb_message("missing_required_field", field="item_code")
    assert "item_code" in msg
