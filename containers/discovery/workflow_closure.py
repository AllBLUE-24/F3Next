"""
Workflow closure rules for Discovery Step 1 MVP validation.

Maps transcript signals and archetype capabilities to ERPNext doctypes —
the deterministic "senior consultant review" after the planner proposes scope.
"""

from __future__ import annotations

import re
from typing import Any, Callable

from containers.discovery.archetype_registry import canonicalize_seed, get_by_id, signal_match_rankings

# Transcript signals beyond recall/expiry (see also mvp_validator._PROBLEM_SIGNALS)
WORKFLOW_SIGNALS: dict[str, tuple[str, ...]] = {
    "manufacturing_execution": (
        r"\bmanufactur",
        r"make[\s-]?to[\s-]?stock",
        r"production batch",
        r"produced",
        r"\bmix(?:ing|ed)?\b",
        r"\bvat\b",
        r"\bbottl",
        r"factory floor",
        r"shop floor",
    ),
    "yield_routing": (
        r"\byield\b",
        r"variance",
        r"\brouting\b",
        r"workstation",
        r"machine time",
        r"each step",
        r"each stage",
        r"mixing stage",
        r"\boperation",
        r"routing process",
    ),
    "wip_visibility": (
        r"black[\s-]?box",
        r"\bwip\b",
        r"work[\s-]?in[\s-]?progress",
        r"factory (?:floor|blind)",
        r"no idea what",
        r"product costing",
        r"inaccurate.*cost",
        r"phantom cost",
    ),
    "material_consumption": (
        r"material consumption",
        r"actual material",
        r"exact material",
        r"consumption at each",
        r"standard vs actual",
    ),
}

# Minimum doctypes required when a workflow signal fires
WORKFLOW_REQUIREMENTS: dict[str, list[str]] = {
    "manufacturing_execution": ["Stock Entry"],
    "yield_routing": ["Job Card", "Stock Entry", "Warehouse"],
    "wip_visibility": ["Stock Entry", "Warehouse"],
    "material_consumption": ["Stock Entry", "Job Card"],
}

# Archetype functional_requirements → ERPNext doctypes (capability law)
FUNCTIONAL_REQUIREMENT_DOCTYPES: dict[str, list[str]] = {
    "track_wip_inventory_by_workstation_warehouse": [
        "Warehouse", "Work Order", "Stock Entry", "Job Card", "Item",
    ],
    "enforce_routing_operations_sequence_control": [
        "BOM", "Work Order", "Job Card", "Stock Entry",
    ],
    "record_scrap_yields_on_work_order_completion": [
        "BOM", "Work Order", "Stock Entry", "Job Card",
    ],
    "define_scrap_items_in_bom": ["BOM", "Item"],
    "enforce_fifo_batch_selection_logic": ["Batch", "Item", "Warehouse"],
    "track_expiry_and_manufacturing_dates_per_batch": ["Batch", "Item"],
    "track_real_time_stock_balances_across_warehouses": [
        "Item", "Warehouse", "Stock Entry",
    ],
    "automate_excel_bom_import_validation": ["BOM", "Item"],
    "enforce_bom_version_control": ["BOM", "Item"],
}

# Work Order alone does not close the loop — these complete manufacturing MVP
_QUALITY_SIGNALS: tuple[str, ...] = (
    r"quality inspection",
    r"\biso\b",
    r"incoming qc",
    r"quality gate",
    r"certificate of analysis",
    r"\bcoa\b",
    r"quality control",
)


def _needs_quality_inspection(
    transcript: str,
    clarification_answers: dict[str, Any] | None = None,
) -> bool:
    """QI only when transcript or clarifications indicate formal QC — not yield-only costing."""
    answers = clarification_answers or {}
    qg = answers.get("quality_gates")
    if qg == "costing_only":
        return False
    if qg in ("incoming_qc", "stage_qc"):
        return True

    text = transcript.lower()
    if re.search(r"quality_gates:\s*costing_only", text, re.I):
        return False
    if re.search(r"quality_gates:\s*(incoming_qc|stage_qc)", text, re.I):
        return True
    return any(re.search(p, text, re.I) for p in _QUALITY_SIGNALS)


def _should_promote_doctype(
    dt: str,
    transcript: str,
    clarification_answers: dict[str, Any] | None = None,
) -> bool:
    if dt in ("Quality Inspection", "Quality Inspection Template"):
        return _needs_quality_inspection(transcript, clarification_answers)
    return True


_WORK_ORDER_CLOSURE = ("Stock Entry", "Warehouse")
_ROUTING_CLOSURE = ("Job Card", "Stock Entry", "Warehouse")


def detect_workflow_signals(transcript: str) -> set[str]:
    text = transcript.lower()
    hit: set[str] = set()
    for key, patterns in WORKFLOW_SIGNALS.items():
        if any(re.search(p, text, re.I) for p in patterns):
            hit.add(key)
    return hit


def _promote_doctype(
    dt: str,
    *,
    day1: list[str],
    deferred: list[str],
    deferred_set: set[str],
    promoted: list[str],
    template_set: set[str],
    graph_keys: set[str],
    notes: list[str],
    reason: str,
) -> None:
    dt = canonicalize_seed(dt)
    if not dt or dt in day1:
        return
    if dt not in template_set and dt not in graph_keys:
        return
    if dt in deferred_set:
        deferred[:] = [d for d in deferred if d != dt]
        deferred_set.discard(dt)
    day1.append(dt)
    promoted.append(dt)
    notes.append(reason)


def apply_workflow_closure(
    *,
    day1: list[str],
    deferred: list[str],
    deferred_set: set[str],
    promoted: list[str],
    template_set: set[str],
    graph_keys: set[str],
    transcript: str,
    niche_id: str,
    notes: list[str],
    on_missing: Callable[[str, list[str]], None] | None = None,
    clarification_answers: dict[str, Any] | None = None,
) -> None:
    """
    Promote doctypes needed to close the operational loop for stated workflows.

    on_missing(signal, missing_doctypes) is called when promotion could not fill gaps.
    """
    signals = detect_workflow_signals(transcript)
    day1_set = set(day1)

    promote = lambda dt, reason: _promote_doctype(
        dt,
        day1=day1,
        deferred=deferred,
        deferred_set=deferred_set,
        promoted=promoted,
        template_set=template_set,
        graph_keys=graph_keys,
        notes=notes,
        reason=reason,
    )

    has_routing = bool(signals & {"yield_routing", "material_consumption"})
    has_wip_mfg = bool(signals & {"wip_visibility", "manufacturing_execution"})
    has_wo_bom = bool(day1_set & {"Work Order", "BOM"})

    # Manufacturing foundation when shop-floor / yield / WIP signals present
    if signals & {
        "yield_routing", "wip_visibility", "material_consumption", "manufacturing_execution",
    }:
        for dt in ("Item", "BOM", "Work Order"):
            promote(
                dt,
                f"Promoted {dt} — manufacturing workflow foundation for stated bottleneck.",
            )

    # Signal-based requirements
    for signal in signals:
        required = WORKFLOW_REQUIREMENTS.get(signal, [])
        for dt in required:
            promote(
                dt,
                f"Promoted {dt} — transcript signals {signal!r} (workflow closure).",
            )
        still_missing = [d for d in required if d not in set(day1)]
        if still_missing and on_missing:
            on_missing(signal, still_missing)

    day1_set = set(day1)

    # Work Order seeds production but Stock Entry + Warehouse record movement/WIP
    if "Work Order" in day1_set:
        for dt in _WORK_ORDER_CLOSURE:
            promote(
                dt,
                f"Promoted {dt} — Work Order is Day-1; ERPNext manufacture loop requires it.",
            )

    # Routing / yield / machine time with manufacturing context
    if has_routing or (has_wip_mfg and has_wo_bom):
        for dt in _ROUTING_CLOSURE:
            promote(
                dt,
                f"Promoted {dt} — shop-floor routing/yield costing requires operation tracking.",
            )
        # Workstation is graph-valid but often not on F3iche template — promote when routing explicit
        if has_routing and "Workstation" in graph_keys:
            promote(
                "Workstation",
                "Promoted Workstation — machine time per routing step links to Job Card.",
            )

    # Manufacturing + batch trace without Work Order still needs Stock Entry for genealogy
    if "manufacturing_execution" in signals and day1_set & {"Batch", "Item"}:
        if "Stock Entry" not in day1_set:
            promote(
                "Stock Entry",
                "Promoted Stock Entry — manufacturing batch genealogy requires stock movements.",
            )

    # Archetype signal match → functional requirement doctypes
    rankings = signal_match_rankings(transcript, niche_id, top_k=2, min_score=1)
    for rank in rankings:
        entry = get_by_id(rank["archetype_id"], niche_id)
        if not entry or rank["score"] < 2:
            continue
        for req in entry.get("functional_requirements") or []:
            for dt in FUNCTIONAL_REQUIREMENT_DOCTYPES.get(str(req), []):
                if not _should_promote_doctype(dt, transcript, clarification_answers):
                    continue
                promote(
                    dt,
                    f"Promoted {dt} — archetype {entry.get('archetype_id')!r} "
                    f"capability {req!r}.",
                )
        # Promote high-confidence day1_seed_hints not already deferred by planner
        for hint in entry.get("day1_seed_hints") or []:
            dt = canonicalize_seed(str(hint))
            if rank["score"] >= 3 and dt and _should_promote_doctype(dt, transcript, clarification_answers):
                promote(
                    dt,
                    f"Promoted {dt} — strong signal match to {entry.get('archetype_id')!r}.",
                )


__all__ = [
    "FUNCTIONAL_REQUIREMENT_DOCTYPES",
    "WORKFLOW_REQUIREMENTS",
    "WORKFLOW_SIGNALS",
    "apply_workflow_closure",
    "detect_workflow_signals",
]
