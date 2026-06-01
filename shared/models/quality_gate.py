"""
Quality gate contracts — shared between IS and OS pipelines.

Transport-friendly dataclasses for Temporal activities and workflow signals.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Literal, Optional

QualityVerdict = Literal["ok", "retry", "user_gap", "hard_block"]


@dataclass
class StepContract:
    step_name: str
    pipeline: str  # IS | OS
    expected_conditions: List[str] = field(default_factory=list)
    auto_fixable_issues: List[str] = field(default_factory=list)
    user_required_issues: List[str] = field(default_factory=list)
    max_retries: int = 2


@dataclass
class NodeReport:
    step_name: str
    pipeline: str
    node_status: Dict[str, Any] = field(default_factory=dict)
    actual_outputs: Dict[str, Any] = field(default_factory=dict)
    feedback_from_previous_retry: Optional[str] = None


@dataclass
class QualityGateInput:
    pipeline: str
    step_name: str
    contract: Dict[str, Any]
    node_report: Dict[str, Any]
    session_id: str = ""
    project_id: str = ""
    company_slug: str = "unknown"
    retry_count: int = 0


@dataclass
class QualityGateResult:
    verdict: QualityVerdict
    analysis: str
    retry_feedback: Optional[str] = None
    user_gap_description: Optional[str] = None
    auto_corrections: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def envelope_to_dict(env: Any) -> Dict[str, Any]:
    """Serialize NodeStatusEnvelope or dict for quality gate input."""
    if env is None:
        return {}
    if hasattr(env, "__dataclass_fields__"):
        return asdict(env)
    if isinstance(env, dict):
        return env
    return {"status": str(env)}


def build_node_report(
    step_name: str,
    pipeline: str,
    node_status: Any,
    *,
    actual_outputs: Optional[Dict[str, Any]] = None,
    feedback_from_previous_retry: Optional[str] = None,
) -> NodeReport:
    return NodeReport(
        step_name=step_name,
        pipeline=pipeline,
        node_status=envelope_to_dict(node_status),
        actual_outputs=actual_outputs or {},
        feedback_from_previous_retry=feedback_from_previous_retry,
    )
