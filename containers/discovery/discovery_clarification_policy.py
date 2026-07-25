"""
Apply user clarification answers to Day-1 scope after planner draft + workflow closure.

Structural policy keyed on clarification question IDs — not niche or company names.
"""

from __future__ import annotations

from typing import Any

from containers.discovery.archetype_registry import canonicalize_seed


def _answer_values(answers: dict[str, Any], key: str) -> list[str]:
    val = answers.get(key)
    if val is None:
        return []
    raw: list[str]
    if isinstance(val, list):
        raw = [str(v).strip() for v in val if str(v).strip()]
    else:
        raw = [str(val).strip()]
    out: list[str] = []
    for item in raw:
        lowered = item.lower()
        if lowered.startswith("other:"):
            continue
        out.append(lowered)
    return out


def _promote(
    dt: str,
    *,
    day1: list[str],
    deferred: list[str],
    deferred_set: set[str],
    promoted: list[str],
    template_set: set[str],
    notes: list[str],
    reason: str,
) -> None:
    dt = canonicalize_seed(dt)
    if not dt or dt not in template_set:
        return
    if dt in deferred_set:
        deferred[:] = [d for d in deferred if d != dt]
        deferred_set.discard(dt)
    if dt not in day1:
        day1.append(dt)
        promoted.append(dt)
        notes.append(f"Promoted {dt} — {reason}")


def _defer(
    dt: str,
    *,
    day1: list[str],
    deferred: list[str],
    deferred_set: set[str],
    notes: list[str],
    reason: str,
) -> None:
    dt = canonicalize_seed(dt)
    if not dt or dt not in day1:
        return
    day1[:] = [d for d in day1 if d != dt]
    if dt not in deferred_set:
        deferred.append(dt)
        deferred_set.add(dt)
        notes.append(f"Deferred {dt} — {reason}")


def apply_clarification_policy(
    *,
    day1: list[str],
    deferred: list[str],
    deferred_set: set[str],
    promoted: list[str],
    template_set: set[str],
    notes: list[str],
    clarification_answers: dict[str, Any] | None,
) -> None:
    """Adjust Day-1/deferred lists from structured clarification answers."""
    answers = clarification_answers or {}
    if not answers:
        return

    promote = lambda dt, reason: _promote(
        dt,
        day1=day1,
        deferred=deferred,
        deferred_set=deferred_set,
        promoted=promoted,
        template_set=template_set,
        notes=notes,
        reason=reason,
    )
    defer = lambda dt, reason: _defer(
        dt,
        day1=day1,
        deferred=deferred,
        deferred_set=deferred_set,
        notes=notes,
        reason=reason,
    )

    strategy = _answer_values(answers, "manufacturing_strategy")
    trace = _answer_values(answers, "trace_direction")

    if "mts" in strategy and "mto" not in strategy:
        if "downstream" not in trace:
            defer("Sales Order", "make-to-stock — production fills inventory before sales.")
            defer("Quotation", "make-to-stock — quotes not required for Day-1 factory loop.")
        if "Customer" in day1 and "downstream" not in trace:
            defer("Customer", "make-to-stock without recall trace — customer master deferred.")
            defer("Delivery Note", "make-to-stock without dispatch trace — deferred.")

    if "mto" in strategy and "mts" not in strategy:
        if "Work Order" in day1 or "BOM" in day1:
            promote("Sales Order", "make-to-order — production triggered by confirmed orders.")

    if "upstream" in trace:
        promote("Purchase Receipt", "user confirmed upstream raw-material trace.")
        promote("Supplier", "user confirmed upstream raw-material trace.")

    if "downstream" in trace:
        promote("Customer", "user confirmed downstream customer/dispatch trace.")
        promote("Delivery Note", "user confirmed downstream customer/dispatch trace.")

    if "expiry" in trace:
        promote("Batch", "user confirmed expiry/shelf-life batch tracking.")

    if answers.get("routing_depth") in (None, ""):
        pass
    elif str(answers.get("routing_depth")).lower() in ("no",):
        defer("Job Card", "user confirmed total batch yield only — no per-step routing.")
        defer("Workstation", "user confirmed total batch yield only — no per-step routing.")

    qg = _answer_values(answers, "quality_gates")
    if "costing_only" in qg:
        defer("Quality Inspection", "user confirmed costing/yield focus — no QC holds Day-1.")
        defer("Quality Inspection Template", "user confirmed costing/yield focus — no QC holds Day-1.")


def clarification_context_for_explainer(clarification_answers: dict[str, Any] | None) -> str:
    """Human-readable block for workflow explainer prompt."""
    if not clarification_answers:
        return "None — no clarifying questions were required."

    labels = {
        "manufacturing_strategy": {
            "mts": "Make-to-stock (produce to inventory, then sell)",
            "mto": "Make-to-order (produce after customer order)",
            "both": "Mixed MTS and MTO",
        },
        "trace_direction": {
            "upstream": "Trace upstream raw materials / supplier batches",
            "downstream": "Trace downstream customers who received batches",
            "expiry": "Expiry / shelf-life / FEFO rotation",
        },
        "routing_depth": {
            "yes": "Per-step machine time and material consumption (Job Card level)",
            "no": "Total batch input/output only — no per-operation tracking",
        },
        "quality_gates": {
            "costing_only": "Costing and yield visibility only — no formal QC holds",
            "incoming_qc": "Incoming raw material QC required",
            "stage_qc": "QC gates during production stages",
        },
    }

    lines: list[str] = []
    for qid, answer in clarification_answers.items():
        if isinstance(answer, list):
            mapped = [labels.get(qid, {}).get(v, v) for v in answer]
            lines.append(f"- {qid}: {', '.join(mapped)}")
        else:
            val = str(answer).lower()
            lines.append(f"- {qid}: {labels.get(qid, {}).get(val, answer)}")

    lines.append(
        "Narrative MUST align with these answers (e.g. do not describe order-driven production if MTS)."
    )
    return "\n".join(lines)


__all__ = [
    "apply_clarification_policy",
    "clarification_context_for_explainer",
]
