"""Tests for IS chat message persistence helpers."""

from containers.implementation.file_io.persist_chat_message import format_auto_fix_chat_message


def test_format_auto_fix_single_kb_defaults():
    msg = format_auto_fix_chat_message(
        [{"doctype": "Supplier", "op": "apply_kb_defaults", "updated": 6}]
    )
    assert "Supplier" in msg
    assert "KB defaults" in msg


def test_format_auto_fix_multiple():
    msg = format_auto_fix_chat_message(
        [
            {"doctype": "Item", "op": "apply_kb_defaults", "updated": 14},
            {"doctype": "Item", "op": "map_enum", "updated": 3},
        ]
    )
    assert "Item" in msg
    assert "•" in msg or "fixes" in msg.lower()


def test_format_auto_fix_empty():
    assert format_auto_fix_chat_message([]) == ""
