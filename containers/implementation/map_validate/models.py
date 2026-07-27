"""Pydantic models for Step 4 map & validate."""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

ValidationLevel = Literal["pass", "partial", "fail"]


class MapResultRow(BaseModel):
    filename: str
    doctype: str
    passed: bool = False
    record_count: int = 0
    field_mapping: Dict[str, str] = Field(default_factory=dict)
    mapping_methods: Dict[str, str] = Field(default_factory=dict)
    missing_fields: List[str] = Field(default_factory=list)
    messages: List[str] = Field(default_factory=list)


class MapValidateReport(BaseModel):
    """Full Step 4 offline or persisted assess output."""

    map_results: List[MapResultRow] = Field(default_factory=list)
    mapped_doctypes: List[str] = Field(default_factory=list)
    validation_report: Dict[str, Any] = Field(default_factory=dict)
    validation_level: ValidationLevel = "partial"
    import_ready: bool = False
    requires_acknowledgment: bool = False
    executive_summary: str = ""
    error_count: int = 0
    warning_count: int = 0
