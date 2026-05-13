"""
data_readiness_agent/models.py

Pydantic schemas for the Data Readiness Assessment — used as structured LLM
output and as the shape stored in Supabase.
"""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class DoctypeGap(BaseModel):
    """Represents one required doctype whose data coverage is insufficient."""
    doctype: str
    criticality: Literal["critical", "non_critical", "optional"]
    reason: str                      # plain English: why this gap matters
    missing_fields: List[str] = Field(default_factory=list)
    recommendation: str              # what the user should do next
    can_proceed_without: bool        # True if ERPNext has a safe default


class DoctypeReady(BaseModel):
    """Represents one required doctype that has sufficient data."""
    doctype: str
    source_file: str
    coverage_pct: float              # 0.0 – 1.0
    mapped_fields: List[str] = Field(default_factory=list)
    missing_optional_fields: List[str] = Field(default_factory=list)


class UnmappableChunk(BaseModel):
    """A portion of an uploaded file that cannot be matched to any doctype."""
    filename: str
    description: str                 # what this data appears to be
    reason: str                      # why it cannot be mapped


class UserQuestion(BaseModel):
    """A structured question surfaced to the user via the Supervisor UI."""
    id: str
    doctype: str
    question: str
    options: List[str]
    is_blocking: bool                # True → user MUST answer before mapping


class DataReadinessAssessment(BaseModel):
    """
    Full output of the Data Readiness Assessment LLM node.

    Produced by assess_data_readiness activity and stored in
    is_data_readiness_assessments (Supabase).
    """
    ready_doctypes: List[DoctypeReady] = Field(default_factory=list)
    partial_doctypes: List[DoctypeGap] = Field(default_factory=list)
    missing_doctypes: List[DoctypeGap] = Field(default_factory=list)
    unmappable_chunks: List[UnmappableChunk] = Field(default_factory=list)
    gap_report: Dict[str, Any] = Field(default_factory=dict)
    minimum_viable_import_possible: bool = True
    user_action_required: bool = False
    questions_for_user: List[UserQuestion] = Field(default_factory=list)
    executive_summary: str = ""      # ≤3 sentences, shown in the UI banner
    import_readiness_score: float = Field(default=1.0, ge=0.0, le=1.0)
    user_decision: Optional[str] = None
