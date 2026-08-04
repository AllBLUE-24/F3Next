"""Action risk classification for OS and IS confirmation gates."""

from __future__ import annotations

from typing import Any, Literal

from shared.erp_policies.lifecycle import get_lifecycle_config

RiskTier = Literal["low", "medium", "high", "critical"]

_FINANCIAL_DOCTYPES: frozenset[str] = frozenset({
    "Sales Invoice",
    "Purchase Invoice",
    "Payment Entry",
    "Journal Entry",
    "Stock Entry",
    "Delivery Note",
    "Purchase Receipt",
})

_CRITICAL_ACTIONS: frozenset[str] = frozenset({"cancel", "delete"})

_CASCADE_CANCEL_EVENTS: frozenset[str] = frozenset({"on_cancel", "cancel", "cancelled"})

_HIGH_VALUE_THRESHOLD = 500_000.0  # INR — tune per deployment


def is_high_value_transaction(doctype: str, payload: dict[str, Any]) -> bool:
    """True when webhook payload grand_total exceeds cascade alert threshold."""
    for key in ("grand_total", "base_grand_total", "paid_amount", "outstanding_amount"):
        raw = payload.get(key)
        if raw is None:
            continue
        try:
            if float(raw) >= _HIGH_VALUE_THRESHOLD:
                return True
        except (TypeError, ValueError):
            continue
    return False


def classify_cascade_risk(
    doctype: str,
    trigger_event: str,
    *,
    payload: dict[str, Any] | None = None,
) -> RiskTier:
    """Risk tier for reactive cascade notifications."""
    event = (trigger_event or "").lower()
    if event in _CASCADE_CANCEL_EVENTS or "cancel" in event:
        return "critical"
    if payload and is_high_value_transaction(doctype, payload):
        return "high"
    action = "submit" if "submit" in event else "create"
    return classify_action_risk(doctype, action, context="cascade")


def classify_action_risk(
    doctype: str,
    action: str = "create",
    *,
    context: str = "import",
) -> RiskTier:
    """Classify doctype+action into low/medium/high/critical."""
    action = (action or "create").lower()
    if action in _CRITICAL_ACTIONS:
        return "critical"

    if context == "cascade" and action == "submit" and doctype in _FINANCIAL_DOCTYPES:
        return "high"

    lifecycle = get_lifecycle_config(doctype)
    tier = lifecycle.get("import_risk_tier", "low")

    if doctype in _FINANCIAL_DOCTYPES and action in ("create", "submit"):
        return "high"

    if action == "submit" and lifecycle.get("is_submittable"):
        if tier == "low":
            return "medium"
        return tier  # type: ignore[return-value]

    if tier in ("medium", "high", "critical"):
        return tier  # type: ignore[return-value]

    return "low"


def requires_confirmation(
    doctype: str,
    action: str = "create",
    *,
    context: str = "import",
) -> bool:
    """True when user must confirm before proceeding."""
    tier = classify_action_risk(doctype, action, context=context)
    if context == "os" and action == "submit":
        return tier in ("medium", "high", "critical")
    if context == "import" and action == "create":
        return tier in ("high", "critical")
    if context == "import" and action == "submit":
        policy = get_lifecycle_config(doctype).get("auto_submit_on_import", "skip")
        return policy == "ask_user"
    return tier in ("high", "critical")


def build_confirmation_preview(
    *,
    phase_id: str,
    steps: list[dict[str, Any]],
    draft_parents: list[dict[str, Any]] | None = None,
    link_corrections: list[dict[str, Any]] | None = None,
    financial_warnings: list[str] | None = None,
) -> dict[str, Any]:
    """Structured preview for IS execution gate or OS harness."""
    create_steps = [s for s in steps if s.get("action") == "create"]
    high_risk = [
        s.get("doctype")
        for s in create_steps
        if classify_action_risk(str(s.get("doctype", "")), "create") in ("high", "critical")
    ]
    medium_risk = [
        s.get("doctype")
        for s in create_steps
        if classify_action_risk(str(s.get("doctype", "")), "create") == "medium"
    ]
    total_records = sum(int(s.get("records") or 0) for s in create_steps)

    warnings: list[str] = list(financial_warnings or [])
    if draft_parents:
        for dp in draft_parents:
            warnings.append(
                f"Draft {dp.get('doctype')} '{dp.get('name')}' may block "
                f"{', '.join(dp.get('blocks', [])) or 'downstream documents'}"
            )
    if high_risk:
        warnings.append(
            f"Financial/high-risk doctypes in this phase: {', '.join(sorted(set(high_risk)))}"
        )

    requires = bool(
        high_risk
        or draft_parents
        or phase_id == "phase_c_transactional"
    )

    return {
        "phase_id": phase_id,
        "requires_confirmation": requires,
        "total_records": total_records,
        "create_steps": [
            {
                "doctype": s.get("doctype"),
                "records": s.get("records"),
                "risk_tier": classify_action_risk(str(s.get("doctype", "")), "create"),
            }
            for s in create_steps
        ],
        "high_risk_doctypes": sorted(set(high_risk)),
        "medium_risk_doctypes": sorted(set(medium_risk)),
        "draft_parents": draft_parents or [],
        "link_corrections": link_corrections or [],
        "warnings": warnings,
        "message": _build_message(phase_id, create_steps, draft_parents, high_risk),
    }


def _build_message(
    phase_id: str,
    create_steps: list[dict[str, Any]],
    draft_parents: list[dict[str, Any]] | None,
    high_risk: list[str],
) -> str:
    parts: list[str] = []
    if create_steps:
        summary = ", ".join(
            f"{s.get('records', 0)} {s.get('doctype')}"
            for s in create_steps
        )
        parts.append(f"About to import: {summary}.")
    if draft_parents:
        names = ", ".join(f"{d.get('doctype')} {d.get('name')}" for d in draft_parents[:5])
        parts.append(f"Draft parent documents detected ({names}) — submit or confirm to proceed.")
    if high_risk:
        parts.append(
            f"Financial actions involved ({', '.join(sorted(set(high_risk)))}). "
            "Review before confirming."
        )
    if phase_id == "phase_c_transactional" and not parts:
        parts.append("Transactional import phase will write live data to ERPNext.")
    return " ".join(parts) if parts else "Ready to execute import phase."
