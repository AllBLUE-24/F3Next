"""
shared/models/command.py

Pydantic models for the OS command API layer.
Used by: backend/app/api/os_command.py, backend/app/services/os_launcher.py
"""

from __future__ import annotations

from typing import Any, Literal, Optional
from pydantic import BaseModel, Field


# ─── API request / response ───────────────────────────────────────────────────

class CommandRequest(BaseModel):
    """Body for POST /api/os/command"""

    prompt:           str               = Field(..., min_length=1, max_length=2000)
    project_id:       str
    company_id:       str
    user_id:          str
    erp_type:         str               = "erpnext"
    session_id:       Optional[str]     = None
    session_context:  Optional[str]     = None   # JSON string of last N turns


class CommandDispatch(BaseModel):
    """Response for POST /api/os/command — immediately returned, workflow runs async"""

    status:       Literal["dispatched"] = "dispatched"
    workflow_id:  str
    session_id:   str


class ConfirmRequest(BaseModel):
    """Body for POST /api/os/confirm/{workflow_id}"""

    decision: Literal["confirm", "cancel"]


class AnswerRequest(BaseModel):
    """Body for POST /api/os/answer/{workflow_id}"""

    answer: str = Field(..., min_length=1)


# ─── Workflow status (polled by frontend) ─────────────────────────────────────

class ConfirmationPreview(BaseModel):
    action_summary:   str
    entities:         list[str]   = Field(default_factory=list)
    warnings:         list[dict]  = Field(default_factory=list)
    auto_corrections: list[dict]  = Field(default_factory=list)


class ConfirmationRequest(BaseModel):
    """
    Surfaced to the frontend when the workflow pauses.
    type = "ambiguity"    → ClarificationBlock in UI
    type = "confirmation" → ConfirmationBlock in UI
    """

    type:       Literal["ambiguity", "confirmation"]

    # For ambiguity
    question:   Optional[str]               = None
    round:      int                         = 1

    # For confirmation
    risk_level: Optional[str]               = None
    preview:    Optional[ConfirmationPreview] = None


class WorkflowStatus(BaseModel):
    """Response for GET /api/os/status/{workflow_id}"""

    status:               str
    confirmation_request: Optional[ConfirmationRequest] = None


class WorkflowResult(BaseModel):
    """Response for GET /api/os/result/{workflow_id}"""

    status:   Literal["success", "error", "cancelled"]
    response: str                        # Human-readable result string
    result:   Optional[dict[str, Any]]   = None   # Raw ERP response
    errors:   Optional[list[dict]]       = None


# ─── Temporal workflow input / output ─────────────────────────────────────────

class CommandWorkflowInput(BaseModel):
    """Passed as the first argument to ERPOSCommandWorkflow.run()"""

    prompt:          str
    project_id:      str
    company_id:      str
    user_id:         str
    erp_type:        str               = "erpnext"
    session_id:      str               = ""
    session_context: list[dict]        = Field(default_factory=list)


class CommandWorkflowOutput(BaseModel):
    """Returned by ERPOSCommandWorkflow.run()"""

    status:       str       # "success" / "error" / "cancelled"
    response:     str       # Formatted human-readable message
    result:       Optional[dict[str, Any]] = None
    errors:       Optional[list[dict]]     = None