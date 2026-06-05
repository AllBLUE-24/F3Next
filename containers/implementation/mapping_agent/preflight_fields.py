"""Post-mapping required-field preflight (same rules as validate)."""
from __future__ import annotations

from typing import Any, Dict, List

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

    sample = [r for r in records[:10] if isinstance(r, dict)]
    missing_fields: List[str] = []
    messages: List[str] = []

    for field in required:
        present = any(
            field in row and row.get(field) not in (None, "")
            for row in sample
        )
        if not present:
            # Column may exist under different key — check any key containing field
            present = any(
                any(field in str(k) for k in row.keys()) and row.get(field) not in (None, "")
                for row in sample
            )
        if not present:
            missing_fields.append(field)
            messages.append(
                f"Required field '{field}' is missing or empty in your uploaded data."
            )

    return {
        "blocking": bool(missing_fields),
        "missing_fields": missing_fields,
        "messages": messages,
    }
