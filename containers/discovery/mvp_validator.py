"""
Deterministic MVP plan validation for Discovery Step 1.

The planner proposes; this module enforces ERPNext graph law, problem coverage,
and dual-system policy before seeds become the Day-1 contract.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from containers.discovery.archetype_registry import canonicalize_seed

_GRAPH_PATH = (
    Path(__file__).parent.parent / "knowledge_base" / "erpnext" / "erpnext_doctype_graph.json"
)

# Transactional doctypes that require Customer at import time
_TRANSACTIONAL_REQUIRES_CUSTOMER = frozenset({
    "Sales Order", "Sales Invoice", "Delivery Note", "Quotation",
})

# Finance masters deferred under dual-system unless operationally required
_DUAL_SYSTEM_DEFERRABLE = frozenset({
    "Sales Invoice", "Payment Entry", "Quotation",
})

# Masters that must appear in Day-1 uploads when a transactional seed needs them
_PROMOTE_WHEN_REQUIRED = frozenset({"Customer", "Supplier", "Item", "Warehouse", "UOM"})

_PROBLEM_SIGNALS: dict[str, tuple[str, ...]] = {
    "raw_material_trace": (
        r"raw material batch",
        r"raw material",
        r"which raw",
        r"upstream",
        r"incoming batch",
        r"supplier batch",
        r"grn",
        r"purchase receipt",
    ),
    "customer_recall": (
        r"which other customers",
        r"which customers received",
        r"customer.*received.*batch",
        r"recall",
        r"defective",
        r"trace.*customer",
    ),
    "expiry_tracking": (
        r"expiry",
        r"expire",
        r"shelf life",
        r"fefo",
        r"6-month",
        r"6 month",
    ),
    "batch_identity": (
        r"batch number",
        r"batch trace",
        r"lot number",
        r"traceability",
        r"compliance",
    ),
}

_PROBLEM_REQUIREMENTS: dict[str, list[str]] = {
    "raw_material_trace": ["Purchase Receipt", "Supplier"],
    "customer_recall": ["Customer", "Delivery Note"],
    "expiry_tracking": ["Batch"],
    "batch_identity": ["Batch", "Item"],
}

_NICHE_BATCH_EXPIRY_INCOMPATIBLE = frozenset({
    "manufacturing_fabrication_jobshop",
})


@dataclass
class ValidationIssue:
    code: str
    message: str
    severity: str = "error"  # error | warning
    suggested_doctypes: list[str] = field(default_factory=list)


@dataclass
class ValidationResult:
    valid: bool
    day1_doctypes: list[str]
    deferred_doctypes: list[str]
    promoted_doctypes: list[str]
    issues: list[ValidationIssue] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "day1_doctypes": self.day1_doctypes,
            "deferred_doctypes": self.deferred_doctypes,
            "promoted_doctypes": self.promoted_doctypes,
            "issues": [
                {
                    "code": i.code,
                    "message": i.message,
                    "severity": i.severity,
                    "suggested_doctypes": i.suggested_doctypes,
                }
                for i in self.issues
            ],
            "notes": self.notes,
        }


def _load_graph() -> dict[str, Any]:
    with open(_GRAPH_PATH, encoding="utf-8") as f:
        return json.load(f)


def _graph_deps(doctype: str, graph: dict[str, Any]) -> list[str]:
    dt_info = graph.get("doctypes", {}).get(doctype, {})
    raw = dt_info.get("depends_on") or []
    return [
        canonicalize_seed(d.split(" (")[0].strip())
        for d in raw
        if d and not str(d).startswith("all ")
    ]


def _resolve_all_deps(seeds: list[str], graph: dict[str, Any]) -> set[str]:
    all_req: set[str] = set(seeds)
    queue = list(seeds)
    while queue:
        dt = queue.pop(0)
        for dep in _graph_deps(dt, graph):
            if dep not in all_req:
                all_req.add(dep)
                queue.append(dep)
    return all_req


def _detect_problem_signals(transcript: str) -> set[str]:
    text = transcript.lower()
    hit: set[str] = set()
    for key, patterns in _PROBLEM_SIGNALS.items():
        if any(re.search(p, text, re.I) for p in patterns):
            hit.add(key)
    return hit


def _extract_doctype_names(entries: list[Any]) -> list[str]:
    names: list[str] = []
    for entry in entries or []:
        if isinstance(entry, str):
            dt = canonicalize_seed(entry)
        elif isinstance(entry, dict):
            dt = canonicalize_seed(str(entry.get("doctype") or ""))
        else:
            continue
        if dt and dt not in names:
            names.append(dt)
    return names


def _is_dual_system(legacy_system: str) -> bool:
    legacy = legacy_system.lower()
    return any(x in legacy for x in ("tally", "busy", "zoho books"))


def validate_mvp_plan(
    *,
    day1_entries: list[Any],
    deferred_entries: list[Any],
    niche_id: str,
    chat_transcript: str,
    template_seeds: list[str],
    legacy_system: str = "",
    graph: dict[str, Any] | None = None,
) -> ValidationResult:
    """
    Validate and normalize an MVP plan from the planner.

    Promotes required masters into day1, applies problem-coverage rules,
    and returns issues for planner revision when errors remain.
    """
    graph = graph or _load_graph()
    template_set = set(template_seeds)
    graph_keys = set(graph.get("doctypes", {}).keys())

    day1 = _extract_doctype_names(day1_entries)
    deferred = _extract_doctype_names(deferred_entries)
    deferred_set = set(deferred)
    issues: list[ValidationIssue] = []
    notes: list[str] = []
    promoted: list[str] = []

    # Allow graph-extension doctypes not on template (Batch, etc.)
    allowed = template_set | graph_keys

    for dt in day1:
        if dt not in allowed:
            issues.append(ValidationIssue(
                code="UNKNOWN_DOCTYPE",
                message=f"{dt!r} is not on the F3iche template or ERPNext graph",
                severity="error",
            ))

    # Dependency promotion for transactional seeds
    signals = _detect_problem_signals(chat_transcript)
    for dt in list(day1):
        if dt in _TRANSACTIONAL_REQUIRES_CUSTOMER and "Customer" not in day1:
            operational_override = "customer_recall" in signals
            if "Customer" in deferred_set and operational_override:
                deferred = [d for d in deferred if d != "Customer"]
                deferred_set.discard("Customer")
                notes.append(
                    "Promoted Customer into Day-1 — recall trace requires customer master "
                    "(operational, not financial)."
                )
            if "Customer" not in deferred_set:
                day1.append("Customer")
                promoted.append("Customer")
                notes.append(
                    f"Promoted Customer into Day-1 because {dt} requires a customer link at import."
                )
            else:
                issues.append(ValidationIssue(
                    code="CUSTOMER_DEFERRED_WITH_TRANSACTION",
                    message=f"{dt} is Day-1 but Customer is deferred — import will gap",
                    severity="error",
                    suggested_doctypes=["Customer"],
                ))

    # Batch upstream: Supplier often required
    if "Batch" in day1 and "Supplier" not in day1 and "Supplier" not in deferred_set:
        deps = _graph_deps("Batch", graph)
        if "Supplier" in deps:
            signals = _detect_problem_signals(chat_transcript)
            if "raw_material_trace" in signals or "batch_identity" in signals:
                day1.append("Supplier")
                promoted.append("Supplier")
                notes.append("Promoted Supplier for raw-material batch traceability.")

    # Problem coverage rules
    day1_set = set(day1)
    for signal in signals:
        required = _PROBLEM_REQUIREMENTS.get(signal, [])
        missing = [d for d in required if d not in day1_set]
        if not missing:
            continue
        # Promote if on template; at least one from group satisfies raw_material_trace
        if signal == "raw_material_trace":
            if any(d in day1_set for d in ("Purchase Receipt", "Supplier", "Stock Entry")):
                continue
            for candidate in ("Purchase Receipt", "Supplier"):
                if candidate in template_set and candidate not in day1_set:
                    day1.append(candidate)
                    promoted.append(candidate)
                    day1_set.add(candidate)
                    notes.append(f"Promoted {candidate} for upstream raw-material trace.")
                    missing = [d for d in required if d not in day1_set]
                    break
        elif signal == "customer_recall":
            for candidate in ("Delivery Note", "Customer"):
                if candidate not in template_set or candidate in day1_set:
                    continue
                if candidate in deferred_set:
                    deferred = [d for d in deferred if d != candidate]
                    deferred_set.discard(candidate)
                day1.append(candidate)
                promoted.append(candidate)
                day1_set.add(candidate)
                notes.append(f"Promoted {candidate} for downstream customer recall trace.")
            missing = [d for d in required if d not in day1_set]
        if missing:
            issues.append(ValidationIssue(
                code=f"MISSING_{signal.upper()}",
                message=(
                    f"Transcript signals {signal!r} but Day-1 plan omits: {', '.join(missing)}"
                ),
                severity="error",
                suggested_doctypes=missing,
            ))

    # Dual-system: defer invoicing, not operational trace masters
    if _is_dual_system(legacy_system):
        for fin in _DUAL_SYSTEM_DEFERRABLE:
            if fin in day1:
                day1 = [d for d in day1 if d != fin]
                if fin not in deferred_set:
                    deferred.append(fin)
                    deferred_set.add(fin)
                notes.append(f"Deferred {fin} — accounting stays in legacy system.")

    # Niche sanity
    if niche_id in _NICHE_BATCH_EXPIRY_INCOMPATIBLE:
        if signals & {"expiry_tracking", "batch_identity"}:
            issues.append(ValidationIssue(
                code="NICHE_MISMATCH",
                message=(
                    f"Niche {niche_id!r} is for metal job shops; transcript signals "
                    "batch/expiry chemical manufacturing — prefer manufacturing_project_chemical "
                    "or manufacturing_food_batch"
                ),
                severity="warning",
                suggested_doctypes=[],
            ))

    # Cap duplicates, preserve order
    seen: set[str] = set()
    day1_ordered: list[str] = []
    for dt in day1:
        if dt not in seen:
            seen.add(dt)
            day1_ordered.append(dt)

    deferred_ordered: list[str] = []
    seen_def: set[str] = set()
    for dt in deferred:
        if dt not in seen_def and dt not in seen:
            seen_def.add(dt)
            deferred_ordered.append(dt)

    errors = [i for i in issues if i.severity == "error"]
    return ValidationResult(
        valid=len(errors) == 0,
        day1_doctypes=day1_ordered,
        deferred_doctypes=deferred_ordered,
        promoted_doctypes=list(dict.fromkeys(promoted)),
        issues=issues,
        notes=notes,
    )


def validation_errors_for_planner(result: ValidationResult) -> str:
    """Format validation issues for a planner revision prompt."""
    lines: list[str] = []
    for issue in result.issues:
        suffix = ""
        if issue.suggested_doctypes:
            suffix = f" Suggested: {', '.join(issue.suggested_doctypes)}"
        lines.append(f"[{issue.severity.upper()}] {issue.code}: {issue.message}{suffix}")
    for note in result.notes:
        lines.append(f"[NOTE] {note}")
    return "\n".join(lines)


__all__ = [
    "ValidationIssue",
    "ValidationResult",
    "validate_mvp_plan",
    "validation_errors_for_planner",
]
