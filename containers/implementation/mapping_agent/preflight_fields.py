"""Post-mapping required-field preflight (same rules as validate)."""
from __future__ import annotations

from typing import Any, Dict, List

from containers.implementation.is_common.field_presence import missing_required_on_records
from containers.implementation.is_common.required_fields import get_required_fields


def preflight_mapped_records(
    doctype: str,
    records: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Check mapped payloads against graph/KB required fields.

    Returns {blocking: bool, missing_fields: [...], messages: [...]}
    """
    required = get_required_fields(doctype)
    if not required or not records:
        return {"blocking": False, "missing_fields": [], "messages": []}

    missing_fields = missing_required_on_records(doctype, records, required)
    messages = [
        f"Required field '{field}' is missing or empty in your uploaded data."
        for field in missing_fields
    ]

    return {
        "blocking": bool(missing_fields),
        "missing_fields": missing_fields,
        "messages": messages,
    }
