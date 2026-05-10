"""
shared/models/is_status.py

Shared, serializable contracts for the Implementation System (IS) supervision loop.

These models are intentionally transport-friendly for Temporal (dataclasses with
JSON-serializable fields) and are separate from SQLAlchemy DB models in
shared/models/is_models.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional


NodeStatus = Literal["success", "partial", "failed"]
SupervisorActionType = Literal["auto_fix", "ask_user", "hard_block"]
SupervisorFinalStatus = Literal["resolved", "needs_user_input", "hard_block"]
SupervisorPromptStatus = Literal["open", "answered", "obsolete"]


@dataclass
class NodeStatusEnvelope:
    """
    Standard return contract for KB-touching IS nodes.

    - Keep fields JSON-serializable (dict/list/str/int/float/bool/None).
    - `primary_result` should be small and summarised; the source of truth remains
      Supabase + R2 artifacts written by the node.
    """

    status: NodeStatus
    primary_result: Optional[Any] = None
    errors: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[Dict[str, Any]] = field(default_factory=list)
    missing_information: List[str] = field(default_factory=list)
    conflicts: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.status == "success" and not self.errors

    @staticmethod
    def success(primary_result: Optional[Any] = None) -> "NodeStatusEnvelope":
        return NodeStatusEnvelope(status="success", primary_result=primary_result)

    @staticmethod
    def failed(
        *,
        primary_result: Optional[Any] = None,
        errors: Optional[List[Dict[str, Any]]] = None,
        warnings: Optional[List[Dict[str, Any]]] = None,
        missing_information: Optional[List[str]] = None,
        conflicts: Optional[List[Dict[str, Any]]] = None,
    ) -> "NodeStatusEnvelope":
        return NodeStatusEnvelope(
            status="failed",
            primary_result=primary_result,
            errors=errors or [],
            warnings=warnings or [],
            missing_information=missing_information or [],
            conflicts=conflicts or [],
        )

    @staticmethod
    def partial(
        *,
        primary_result: Optional[Any] = None,
        errors: Optional[List[Dict[str, Any]]] = None,
        warnings: Optional[List[Dict[str, Any]]] = None,
        missing_information: Optional[List[str]] = None,
        conflicts: Optional[List[Dict[str, Any]]] = None,
    ) -> "NodeStatusEnvelope":
        return NodeStatusEnvelope(
            status="partial",
            primary_result=primary_result,
            errors=errors or [],
            warnings=warnings or [],
            missing_information=missing_information or [],
            conflicts=conflicts or [],
        )


@dataclass
class SupervisorAction:
    id: str
    type: SupervisorActionType
    scope: str
    changes: List[Dict[str, Any]] = field(default_factory=list)
    question: Optional[str] = None
    options: Optional[List[str]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SupervisorResult:
    actions: List[SupervisorAction] = field(default_factory=list)
    summary_for_ui: str = ""
    final_status: SupervisorFinalStatus = "resolved"


@dataclass
class SupervisorPrompt:
    """
    Persistent prompt record contract.

    The DB table representation may store these fields as JSONB; this dataclass is
    used for transport and API serialization.
    """

    id: str
    project_id: str
    step: str
    status: SupervisorPromptStatus = "open"
    node_status: Optional[NodeStatusEnvelope] = None
    actions: List[SupervisorAction] = field(default_factory=list)
    summary_for_ui: str = ""
    answer_payload: Optional[Dict[str, Any]] = None


@dataclass
class ApplySupervisorActionsInput:
    project_id: str
    session_id: Optional[str] = None
    prompt_id: Optional[str] = None
    step: str = ""
    company_slug: Optional[str] = None
    actions: List[SupervisorAction] = field(default_factory=list)


@dataclass
class ApplyActionsResult:
    applied: List[Dict[str, Any]] = field(default_factory=list)
    skipped: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[Dict[str, Any]] = field(default_factory=list)

