"""Tests for Day-1 upload schema preview from field_mappings KB."""

from __future__ import annotations

from containers.discovery.upload_schema_preview import build_upload_schema_preview


def test_batch_has_required_columns_from_kb():
    preview = build_upload_schema_preview(["Batch"])
    batch = preview["Batch"]
    assert batch["kb_available"] is True
    required_fields = {c["field"] for c in batch["required_columns"]}
    assert "batch_id" in required_fields
    assert "item" in required_fields


def test_unknown_doctype_marks_kb_unavailable():
    preview = build_upload_schema_preview(["TotallyFakeDoctype"])
    assert preview["TotallyFakeDoctype"]["kb_available"] is False


def test_item_preview_includes_mandatory_fields():
    preview = build_upload_schema_preview(["Item"])
    item = preview["Item"]
    assert item["kb_available"] is True
    assert len(item["required_columns"]) >= 1
