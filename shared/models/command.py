"""
shared/models/command.py
"""
from typing import Any, Optional
from pydantic import BaseModel

class CommandRequest(BaseModel):
    prompt: str
    project_id: str
    company_id: str
    user_id: str
    erp_type: str = "erpnext"
    session_id: Optional[str] = None
    session_context: Optional[str] = None
    mode: str = "execute"
    seed_context: Optional[dict[str, Any]] = None
    origin_notification_id: Optional[str] = None

class CommandWorkflowInput(BaseModel):
    prompt: str
    project_id: str
    company_id: str
    user_id: str
    erp_type: str
    session_id: str
    session_context: list[dict]
    mode: str = "execute"
    seed_context: Optional[dict[str, Any]] = None
    origin_notification_id: Optional[str] = None

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
    field: Optional[str] = None
    candidates: Optional[list[str]] = None
    severity: Optional[str] = None
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


class NotificationReplyRequest(BaseModel):
    user_id: str
    company_id: str
    prompt: str
    mode: str = "execute"


class NotificationReplyResponse(BaseModel):
    workflow_id: str
    session_id: str
    notification_id: str

class CommandWorkflowOutput(BaseModel):
    status: str
    response: str
    result: Optional[dict] = None
    errors: Optional[list] = []