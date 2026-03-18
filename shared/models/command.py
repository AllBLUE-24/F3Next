"""
shared/models/command.py
"""
from typing import Optional
from pydantic import BaseModel

class CommandRequest(BaseModel):
    prompt: str
    project_id: str
    company_id: str
    user_id: str
    erp_type: str = "erpnext"
    session_id: Optional[str] = None
    session_context: Optional[str] = None
    mode: str = "execute"  # 🔴 NEW: Accept explicit mode from UI

class CommandWorkflowInput(BaseModel):
    prompt: str
    project_id: str
    company_id: str
    user_id: str
    erp_type: str
    session_id: str
    session_context: list[dict]
    mode: str = "execute"  # 🔴 NEW: Pass it into Temporal

class CommandDispatch(BaseModel):
    status: str
    workflow_id: str
    session_id: str

class ConfirmRequest(BaseModel):
    decision: str

class AnswerRequest(BaseModel):
    answer: str

class ConfirmationPreview(BaseModel):
    action_summary: str
    entities: list[str]
    warnings: list[dict]
    auto_corrections: list[dict]

class ConfirmationRequest(BaseModel):
    type: str
    question: Optional[str] = None
    round: Optional[int] = None
    risk_level: Optional[str] = None
    preview: Optional[ConfirmationPreview] = None

class WorkflowStatus(BaseModel):
    status: str
    confirmation_request: Optional[ConfirmationRequest] = None
    response: Optional[str] = None

class WorkflowResult(BaseModel):
    status: str
    response: str
    result: Optional[dict] = None
    errors: Optional[list] = []

class CommandWorkflowOutput(BaseModel):
    status: str
    response: str
    result: Optional[dict] = None
    errors: Optional[list] = []