"""
Day-1 upload schema preview — required/optional spreadsheet columns per doctype.

Sourced from field_mappings KB (same contract Step 2 mapping uses), not hardcoded
per test fixture.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_FIELD_MAPPINGS_PATH = (
    Path(__file__).parent.parent
    / "knowledge_base"
    / "erpnext"
    / "schema"
    / "field_mappings.json"
)

_MAX_OPTIONAL = 8


def _load_field_mappings() -> dict[str, Any]:
    with open(_FIELD_MAPPINGS_PATH, encoding="utf-8") as f:
        return json.load(f)


def _column_entry(fieldname: str, spec: dict[str, Any]) -> dict[str, Any]:
    synonyms = list(spec.get("user_input_synonyms") or [])
    label = (synonyms[0] if synonyms else fieldname).replace("_", " ")
    return {
        "field": fieldname,
        "label": label,
        "synonyms": synonyms[:4],
        "fieldtype": spec.get("fieldtype", ""),
    }


def build_upload_schema_preview(seed_doctypes: list[str]) -> dict[str, dict[str, Any]]:
    """
    Return upload column guidance for each Day-1 seed doctype.

    Keys: doctype name. Values: required_columns, optional_columns, kb_available.
    """
    kb = _load_field_mappings()
    doctypes_kb = kb.get("doctypes") or {}
    preview: dict[str, dict[str, Any]] = {}

    for dt in seed_doctypes or []:
        entry = doctypes_kb.get(dt)
        if not entry:
            preview[dt] = {
                "required_columns": [],
                "optional_columns": [],
                "kb_available": False,
            }
            continue

        mandatory_names = set(entry.get("mandatory_fields") or [])
        required: list[dict[str, Any]] = []
        optional: list[dict[str, Any]] = []

        for fieldname, spec in (entry.get("field_mappings") or {}).items():
            col = _column_entry(fieldname, spec)
            is_required = bool(spec.get("mandatory")) or fieldname in mandatory_names
            if is_required:
                required.append(col)
            else:
                optional.append(col)

        preview[dt] = {
            "required_columns": required,
            "optional_columns": optional[:_MAX_OPTIONAL],
            "kb_available": bool(required or optional),
        }

    return preview


__all__ = ["build_upload_schema_preview"]
