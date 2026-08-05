"""Pydantic models for Step 5 phased import."""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

ImportLevel = Literal["success", "partial", "failed", "blocked"]
PlanStatus = Literal["ready", "ready_with_gaps", "blocked"]


class ImportStepRow(BaseModel):
    phase_id: str
    doctype: str
    action: str
    records: int = 0
    data_source: str = ""
    criticality: Optional[str] = None


class ImportExecutionReport(BaseModel):
    """Full Step 5 offline or persisted assess output."""

    plan_status: PlanStatus = "blocked"
    import_level: ImportLevel = "blocked"
    import_ready: bool = False
    phases: Dict[str, Any] = Field(default_factory=dict)
    steps: List[ImportStepRow] = Field(default_factory=list)
    create_step_count: int = 0
    data_gap_count: int = 0
    optional_gap_count: int = 0
    ordered_phase_ids: List[str] = Field(default_factory=list)
    executive_summary: str = ""
    blocked_reasons: List[str] = Field(default_factory=list)
