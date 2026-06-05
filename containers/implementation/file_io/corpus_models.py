"""Pydantic schemas for LLM corpus understanding (Step 2b)."""
from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field


class ColumnInterpretation(BaseModel):
    column: str
    meaning: str = Field(description="Plain English meaning of this column")


class FileUnderstanding(BaseModel):
    filename: str
    business_description: str = Field(
        description="Plain English: what business data this file contains"
    )
    likely_entity_types: List[str] = Field(
        default_factory=list,
        description="Business entities present, e.g. Customer, Supplier, Project",
    )
    likely_erpnext_doctypes: List[str] = Field(
        default_factory=list,
        description="ERPNext doctypes this file most likely maps to",
    )
    explicitly_not_doctypes: List[str] = Field(
        default_factory=list,
        description="ERPNext doctypes this file is clearly NOT, e.g. client orders ≠ Work Order",
    )
    column_interpretations: List[ColumnInterpretation] = Field(
        default_factory=list,
        description="Per-column plain English meaning (list avoids Gemini additionalProperties issues)",
    )
    confidence: float = Field(ge=0.0, le=1.0, default=0.7)
    reasoning_signals: List[str] = Field(default_factory=list)


class CorpusUnderstanding(BaseModel):
    corpus_summary: str = Field(
        description="One paragraph summarizing the whole upload batch"
    )
    files: List[FileUnderstanding] = Field(default_factory=list)
