"""Pydantic schemas for F3iche confirmation synthesis (Step 3.5)."""
from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class F3icheConfirmationSynthesis(BaseModel):
    """LLM output: merged file + discovery proposal for user confirmation."""

    confirmation_message: str = Field(
        description="Natural language question asking user to confirm business type"
    )
    proposed_f3iche: str = Field(description="Niche ID from signals_registry niche_ids")
    proposed_industry: str = Field(description="Specific industry string")
    display_name: str = Field(description="Human-readable business type label")
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_from_files: List[str] = Field(default_factory=list)
    evidence_from_discovery: List[str] = Field(default_factory=list)
    conflicts: List[str] = Field(
        default_factory=list,
        description="Plain English notes where discovery and files disagree",
    )
    alignment: Literal["agree", "partial", "conflict"] = "agree"


class F3icheCorrectionResolution(BaseModel):
    """Map user's free-text correction to a niche ID."""

    f3iche: str
    industry: str
    display_name: str
    reasoning: str = ""
