"""
Helpers for provider-agnostic structured LLM output.

OpenAI json_object mode does not enforce Pydantic schemas — we repair common
omissions/aliases before validation.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Type, get_args, get_origin

from pydantic import BaseModel


def build_structured_system_instruction(schema: Type[BaseModel]) -> str:
    """System prompt listing required JSON shape for json_object mode."""
    example = _example_skeleton(schema)
    return (
        "You are a structured data extraction engine. "
        "Respond with a single JSON object only — no markdown, no commentary. "
        "Include EVERY required field shown in the schema below. "
        "Use empty strings or empty arrays when unknown — never omit required keys.\n\n"
        f"REQUIRED JSON SHAPE:\n{json.dumps(example, indent=2)}"
    )


def _example_skeleton(schema: Type[BaseModel]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for name, field in schema.model_fields.items():
        ann = field.annotation
        origin = get_origin(ann)
        if origin is list:
            args = get_args(ann)
            inner = args[0] if args else str
            if isinstance(inner, type) and issubclass(inner, BaseModel):
                out[name] = [_example_skeleton(inner)]
            else:
                out[name] = []
        elif isinstance(ann, type) and issubclass(ann, BaseModel):
            out[name] = _example_skeleton(ann)
        elif ann is float or ann is int:
            out[name] = 0.0
        else:
            out[name] = ""
    return out


def repair_pydantic_dict(data: Any, schema: Type[BaseModel]) -> Dict[str, Any]:
    """Normalize common LLM JSON drift before Pydantic validation."""
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object, got {type(data).__name__}")

    repaired = dict(data)

    # CorpusUnderstanding aliases
    if schema.__name__ == "CorpusUnderstanding":
        if not repaired.get("corpus_summary"):
            for alias in ("summary", "corpusSummary", "overview", "description"):
                if repaired.get(alias):
                    repaired["corpus_summary"] = repaired[alias]
                    break
        if not repaired.get("corpus_summary") and isinstance(repaired.get("files"), list):
            descs = [
                str(f.get("business_description") or "").strip()
                for f in repaired["files"]
                if isinstance(f, dict)
            ]
            repaired["corpus_summary"] = (
                "; ".join(d for d in descs if d)
                or "Uploaded business data files for ERP implementation."
            )
        if "files" not in repaired and "file_understandings" in repaired:
            repaired["files"] = repaired["file_understandings"]

    if "files" in repaired and isinstance(repaired["files"], list):
        repaired["files"] = [_repair_file_entry(f) for f in repaired["files"] if isinstance(f, dict)]

    # Fill any still-missing required top-level fields with safe defaults
    for name, field in schema.model_fields.items():
        if name in repaired and repaired[name] is not None:
            continue
        if field.is_required():
            ann = field.annotation
            origin = get_origin(ann)
            if origin is list:
                repaired[name] = []
            elif ann is float:
                repaired[name] = 0.0
            elif ann is int:
                repaired[name] = 0
            else:
                repaired[name] = ""

    return repaired


def _repair_file_entry(entry: Dict[str, Any]) -> Dict[str, Any]:
    f = dict(entry)
    if not f.get("filename"):
        f["filename"] = f.get("file_name") or f.get("name") or "unknown.csv"
    if not f.get("business_description"):
        f["business_description"] = f.get("description") or "(file present in upload batch)"
    for list_field in (
        "likely_entity_types",
        "likely_erpnext_doctypes",
        "explicitly_not_doctypes",
        "reasoning_signals",
    ):
        if list_field not in f or f[list_field] is None:
            f[list_field] = []
    if "confidence" not in f or f["confidence"] is None:
        f["confidence"] = 0.7
    cols = f.get("column_interpretations")
    if isinstance(cols, dict):
        f["column_interpretations"] = [
            {"column": str(k), "meaning": str(v)} for k, v in cols.items()
        ]
    elif cols is None:
        f["column_interpretations"] = []
    return f
