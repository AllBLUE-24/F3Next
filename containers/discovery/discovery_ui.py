"""
User-facing copy for Discovery Step 1 — no internal planner/validator strings in UI.
"""

from __future__ import annotations

import re
from typing import Any

from containers.discovery.discovery_assurance import AssuranceResult

_OTHER_PREFIX = "other:"


def humanize_assurance(result: AssuranceResult) -> dict[str, Any]:
    """Return assurance payload safe for frontend (no internal diagnostics)."""
    user_reasons = [_map_assurance_reason(r) for r in result.reasons]
    return {
        "level": result.level,
        "reasons": user_reasons,
        "requires_acknowledgment": result.level == "yellow",
    }


def _map_assurance_reason(internal: str) -> str:
    text = internal.lower()
    if "weak archetype" in text or "signal match" in text:
        return (
            "We inferred your business pattern from limited signals in the chat — "
            "please review the Day-1 module list before confirming."
        )
    if "validator promoted" in text or "promoted" in text and "module" in text:
        return (
            "We added a few modules beyond the first draft to match what you described. "
            "Check items marked as recommended below."
        )
    if "clarifying questions" in text or "skipped or incomplete" in text:
        return "Some scoping questions were not answered — assumptions may remain in the plan."
    if "closure test missing" in text:
        return "We could not verify a clear Day-1 success test for your stated bottleneck."
    if "offline fallback" in text or "offline draft" in text:
        return (
            "This plan used a conservative offline template — review scope carefully "
            "before upload."
        )
    if "no f3iche" in text or "generic seeds" in text:
        return (
            "We do not yet have a full industry template for your niche — "
            "Day-1 scope uses core ERPNext modules only."
        )
    if "org structure not confirmed" in text:
        return internal.replace("Org structure not confirmed in discovery: ", "Please confirm: ")
    if "limited coverage" in text or "missing industry" in text:
        return "We are missing a few basics from the chat (industry, pain point, or current system)."
    if "structural closure passed" in text:
        return "Day-1 scope aligns with your bottleneck and the answers you provided."
    if "validation failed" in text or "missing bom" in text:
        return internal
    # Validator warning passthrough — strip jargon where possible
    if "scale_breadth" in text:
        return "Day-1 includes many modules for your stated company size — consider deferring some."
    return _sanitize_validator_message(internal)


def _sanitize_validator_message(message: str) -> str:
    cleaned = re.sub(r"\bSCALE_BREADTH_\w+\b", "scope breadth", message)
    cleaned = re.sub(r"\bniche_id\b", "industry profile", cleaned, flags=re.I)
    return cleaned


def humanize_promotion_labels(
    promoted_doctypes: list[str],
    promotion_reasons: dict[str, str] | None = None,
) -> dict[str, str]:
    """Short user-facing badge text per promoted doctype."""
    reasons = promotion_reasons or {}
    out: dict[str, str] = {}
    for dt in promoted_doctypes:
        raw = (reasons.get(dt) or "").lower()
        if any(k in raw for k in ("trace", "batch", "recall", "expiry", "fefo")):
            out[dt] = "Added for traceability"
        elif any(k in raw for k in ("customer", "delivery", "dispatch", "downstream")):
            out[dt] = "Added for customer dispatch trace"
        elif any(k in raw for k in ("purchase", "supplier", "upstream", "raw")):
            out[dt] = "Added for raw-material trace"
        elif any(k in raw for k in ("sales order", "order-driven", "mto")):
            out[dt] = "Added for order-driven production"
        elif any(k in raw for k in ("job card", "routing", "yield", "wip")):
            out[dt] = "Added for shop-floor visibility"
        else:
            out[dt] = "Recommended for Day-1"
    return out


def humanize_validator_warnings(warnings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """User-facing validator notes (no internal codes)."""
    out: list[dict[str, Any]] = []
    for w in warnings:
        msg = _sanitize_validator_message(str(w.get("message") or ""))
        suggested = w.get("suggested_doctypes") or []
        out.append({
            "message": msg,
            "suggested_doctypes": suggested,
        })
    return out


def build_workflow_preview_ui_payload(
    *,
    metadata: dict[str, Any],
    workflow_explanation: dict[str, Any],
    seed_doctypes: list[str],
    deferred_doctypes: list[str] | None = None,
    required_doctypes: list[str] | None = None,
    promoted_doctypes: list[str] | None = None,
) -> dict[str, Any]:
    """Assemble workflow preview fields safe for frontend."""
    promoted = promoted_doctypes or []
    promotion_reasons = metadata.get("promotion_reasons") or {}
    validator_warnings = metadata.get("validator_warnings") or []
    assurance_raw = metadata.get("assurance") or {}

    if "requires_acknowledgment" in assurance_raw:
        assurance_ui = assurance_raw
    else:
        assurance_ui = humanize_assurance(
            AssuranceResult(
                level=assurance_raw.get("level", "yellow"),
                reasons=assurance_raw.get("reasons") or [],
            )
        )

    return {
        "workflow_explanation": workflow_explanation,
        "seed_doctypes": seed_doctypes,
        "deferred_doctypes": deferred_doctypes or [],
        "required_doctypes": required_doctypes or [],
        "promoted_doctypes": promoted,
        "dual_system_note": metadata.get("dual_system_note")
        or (metadata.get("target_structure") or {}).get("dual_system_note")
        or "",
        "assurance": assurance_ui,
        "closure_test": metadata.get("closure_test", ""),
        "promotion_labels": humanize_promotion_labels(promoted, promotion_reasons),
        "validator_warnings": humanize_validator_warnings(validator_warnings),
        "upload_schema_preview": metadata.get("upload_schema_preview") or {},
    }


def strip_internal_discovery_fields(metadata: dict[str, Any]) -> dict[str, Any]:
    """Remove fields that must not drive UI copy."""
    cleaned = dict(metadata)
    for key in (
        "plan_reasoning",
        "scoping_reasoning",
        "niche_resolution_source",
        "promotion_reasons",
    ):
        cleaned.pop(key, None)
    assurance = cleaned.get("assurance")
    if isinstance(assurance, dict):
        assurance = dict(assurance)
        for key in ("signal_top_score", "signal_margin", "promotion_count", "validator_valid", "warning_count"):
            assurance.pop(key, None)
        cleaned["assurance"] = assurance
    return cleaned


__all__ = [
    "humanize_assurance",
    "humanize_promotion_labels",
    "humanize_validator_warnings",
    "build_workflow_preview_ui_payload",
    "strip_internal_discovery_fields",
]
