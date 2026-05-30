"""Workflow sandbox-safe gate helpers."""

from containers.os.os_workflow.workflow_gates import (
    ERP_AUTOFILL_FIELDS,
    is_autofill_field,
    is_fixable_validation,
)


def test_autofill_fields_include_title() -> None:
    assert "title" in ERP_AUTOFILL_FIELDS
    assert is_autofill_field("title")


def test_fixable_skips_autofill_mandatory() -> None:
    validation = {
        "valid": False,
        "errors": [
            {"rule_id": "mandatory_fields", "field": "title", "message": "missing title"},
        ],
    }
    assert is_fixable_validation(validation) is False


def test_fixable_unknown_customer() -> None:
    validation = {
        "valid": False,
        "errors": [
            {"rule_id": "unknown_customer", "field": "customer", "message": "missing"},
        ],
    }
    assert is_fixable_validation(validation) is True
