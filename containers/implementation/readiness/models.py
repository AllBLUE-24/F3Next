"""Pydantic models for Step 3 readiness (extends data_readiness_agent shapes)."""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from containers.implementation.data_readiness_agent.models import (
    AssumedField,
    DataReadinessAssessment,
    DoctypeGap,
    DoctypeReady,
    UnmappableChunk,
    UserQuestion,
)

ReadinessLevel = Literal["green", "yellow", "red"]
MatrixRowStatus = Literal["ready", "partial", "missing", "deferred", "overclaim", "info"]


class MatrixRow(BaseModel):
    """One row in the MVP × file × field readiness table."""

    filename: str
    doctype: str
    in_mvp_scope: bool = True
    corpus_claims: bool = False
    evidenced: bool = False
    field_provable: bool = False
    ready: bool = False
    corpus_overclaim: bool = False
    required_fields: List[str] = Field(default_factory=list)
    present_fields: List[str] = Field(default_factory=list)
    missing_fields: List[str] = Field(default_factory=list)
    assumed_fields: List[AssumedField] = Field(default_factory=list)
    blocking_fields: List[str] = Field(default_factory=list)
    status: MatrixRowStatus = "missing"
    evidence_type: Optional[str] = None
    file_evidence_score: float = 0.0


class ReadinessMatrix(BaseModel):
    rows: List[MatrixRow] = Field(default_factory=list)
    overclaims: List[Dict[str, Any]] = Field(default_factory=list)
    summary: Dict[str, Any] = Field(default_factory=dict)


class FieldGap(BaseModel):
    doctype: str
    field: str
    source_file: Optional[str] = None
    tier: Literal["critical", "important", "info"] = "critical"
    reason: str = ""


class ReadinessReport(DataReadinessAssessment):
    """Full Step 3 output — deterministic core + optional LLM narrative."""

    matrix: ReadinessMatrix = Field(default_factory=ReadinessMatrix)
    readiness_level: ReadinessLevel = "yellow"
    field_gaps: List[FieldGap] = Field(default_factory=list)
    gap_items: List[Dict[str, Any]] = Field(default_factory=list)
    schema_sources: Dict[str, str] = Field(default_factory=dict)
    pre_analysis: Dict[str, Any] = Field(default_factory=dict)
