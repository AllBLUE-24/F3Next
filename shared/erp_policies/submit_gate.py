"""
Unified submit-after-create policy for IS import and OS execution (COMMIT gate).

Axis 1 — Dependency: submit parent when a child in the same wave requires it.
Axis 2 — Confidence + risk: auto-submit when commit_confidence >= threshold and
         risk tier allows (high/critical require execution_confirmed on import).
"""

from __future__ import annotations

from typing import Literal, Optional

from shared.erp_policies.action_risk import classify_action_risk
from shared.erp_policies.lifecycle import children_requiring_submitted, is_submittable

COMMIT_CONFIDENCE_AUTO_SUBMIT_THRESHOLD = 0.8

Context = Literal["import", "os"]


def phase_child_doctypes(steps: list[dict]) -> set[str]:
    """Create-action doctypes in the current execution wave."""
    return {
        str(s.get("doctype"))
        for s in (steps or [])
        if s.get("action") == "create" and s.get("doctype")
    }


def all_plan_create_doctypes(phases: dict) -> set[str]:
    """Create-action doctypes across all import phases (for cross-phase dependencies)."""
    out: set[str] = set()
    for phase_def in (phases or {}).values():
        if isinstance(phase_def, dict):
            out |= phase_child_doctypes(phase_def.get("steps") or [])
    return out


def is_dependency_submit_required(
    parent_doctype: str,
    child_doctypes: set[str],
) -> bool:
    """True when a child in this wave requires parent to be submitted."""
    if not parent_doctype or not child_doctypes:
        return False
    required_children = set(children_requiring_submitted(parent_doctype))
    return bool(required_children & child_doctypes)


def should_submit_after_create(
    doctype: str,
    *,
    context: Context = "import",
    commit_confidence: float = 1.0,
    phase_child_doctypes: Optional[set[str]] = None,
    execution_confirmed: bool = False,
    override: Optional[bool] = None,
) -> bool:
    """
    Whether to call submit_document immediately after a successful create.

    Args:
        doctype: ERPNext doctype just created.
        context: ``import`` (IS phased import) or ``os`` (command execution).
        commit_confidence: 0–1 wave confidence (IS readiness score, OS intent).
        phase_child_doctypes: create doctypes in the same import phase / plan.
        execution_confirmed: user approved execution gate (IS) or passed OS confirm.
        override: explicit True/False from harness or caller; None = use policy.
    """
    if not is_submittable(doctype):
        return False

    if override is False:
        return False
    if override is True:
        return True

    children = phase_child_doctypes or set()

    # Axis 1 — structural dependency (e.g. BOM before Work Order in same phase)
    if is_dependency_submit_required(doctype, children):
        return True

    risk = classify_action_risk(doctype, "submit", context=context)

    # High/critical financial docs: only after explicit confirmation
    if risk in ("high", "critical"):
        if context == "os":
            return execution_confirmed
        return execution_confirmed

    # Axis 2 — confidence gate for medium/low risk submittable docs
    if commit_confidence >= COMMIT_CONFIDENCE_AUTO_SUBMIT_THRESHOLD:
        return True

    # User confirmed full phase despite lower confidence
    if execution_confirmed and risk == "medium":
        return True

    return False
