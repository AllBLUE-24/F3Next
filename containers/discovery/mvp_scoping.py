"""
Bottleneck-driven MVP seed scoping for Discovery Assistant Step 1.

Narrows f3iche template seeds to Day-1 MVP based on discovery context —
not the full mandatory_doctypes list.
"""

from __future__ import annotations

import re
from typing import Any

# Bottleneck / transcript signals → minimal Day-1 doctypes (subset of any f3iche template)
_SCOPING_RULES: list[dict[str, Any]] = [
    {
        "id": "factory_wip_bridge",
        "patterns": [
            r"work[\s-]?in[\s-]?progress",
            r"\bwip\b",
            r"black\s+box",
            r"factory\s+floor",
            r"production\s+schedule",
            r"batch[\s-]?wise",
            r"disconnected\s+excel",
            r"excel\s+sheet",
            r"formulation",
            r"\bbom\b",
        ],
        "mvp_doctypes": ["Item", "BOM", "Sales Order", "Work Order", "Stock Entry"],
        "optional_if_mentioned": {
            r"\bbatch\b": "Batch",
            r"job\s+card|shop\s+floor": "Job Card",
            r"\bproject\b|installation|site\s+work|turnkey": "Project",
        },
        "reasoning": (
            "Day-1 MVP bridges factory WIP: product master, formulations (BOM), "
            "sales bookings driving production, work orders, and stock movement."
        ),
    },
    {
        "id": "inventory_visibility",
        "patterns": [
            r"stockout",
            r"inventory\s+visibility",
            r"warehouse",
            r"stock\s+reconcil",
        ],
        "mvp_doctypes": ["Item", "Warehouse", "Stock Entry", "Sales Order", "Purchase Order"],
        "optional_if_mentioned": {},
        "reasoning": "Day-1 MVP focuses on inventory visibility and stock movement.",
    },
    {
        "id": "procurement_gap",
        "patterns": [
            r"purchase\s+order",
            r"procurement",
            r"supplier\s+order",
            r"untracked\s+supplier",
        ],
        "mvp_doctypes": ["Supplier", "Item", "Purchase Order", "Purchase Receipt"],
        "optional_if_mentioned": {},
        "reasoning": "Day-1 MVP focuses on procurement and supplier order tracking.",
    },
]

_MAX_DAY1_SEEDS = 8


def _combined_context(
    *,
    mvp_focus: dict[str, Any] | None,
    coverage: dict[str, Any] | None,
    chat_transcript: str,
) -> str:
    parts: list[str] = []
    if mvp_focus:
        parts.append(str(mvp_focus.get("primary_bottleneck") or ""))
        for req in mvp_focus.get("functional_requirements") or []:
            parts.append(str(req))
    if coverage:
        for key in ("pain_point", "legacy_system", "strategy", "industry", "scale"):
            entry = coverage.get(key) or {}
            if entry.get("value"):
                parts.append(str(entry["value"]))
    parts.append(chat_transcript or "")
    return " ".join(parts).lower()


def _match_rule(context: str) -> dict[str, Any] | None:
    for rule in _SCOPING_RULES:
        if any(re.search(p, context, re.I) for p in rule["patterns"]):
            return rule
    return None


def _legacy_accounting_system(coverage: dict[str, Any] | None) -> str:
    if not coverage:
        return ""
    legacy = coverage.get("legacy_system") or {}
    return str(legacy.get("value") or "").lower()


def scope_mvp_seeds(
    *,
    template_seeds: list[str],
    f3iche_data: dict[str, Any] | None = None,
    mvp_focus: dict[str, Any] | None = None,
    coverage: dict[str, Any] | None = None,
    chat_transcript: str = "",
    user_confirmed_override: list[str] | None = None,
) -> dict[str, Any]:
    """
    Return bottleneck-scoped Day-1 seeds and deferred modules.

    Returns:
        mvp_seeds, deferred_seeds, scoping_mode, scoping_reasoning, dual_system_note
    """
    template_set = list(dict.fromkeys(template_seeds))
    policy = (f3iche_data or {}).get("import_field_policy") or {}
    policy_defer = set(policy.get("defer_until_post_mvp") or [])
    policy_always = set(policy.get("always_ask") or [])

    if user_confirmed_override:
        confirmed = [d for d in user_confirmed_override if d in template_set]
        deferred = [d for d in template_set if d not in confirmed]
        return {
            "mvp_seeds": confirmed,
            "deferred_seeds": deferred,
            "scoping_mode": "user_confirmed",
            "scoping_reasoning": "User confirmed module selection.",
            "dual_system_note": "",
        }

    context = _combined_context(
        mvp_focus=mvp_focus,
        coverage=coverage,
        chat_transcript=chat_transcript,
    )
    legacy = _legacy_accounting_system(coverage)
    dual_system_note = ""
    if any(x in legacy for x in ("tally", "busy", "zoho books")):
        dual_system_note = (
            "Accounting stays in your current system; ERPNext Day-1 focuses on "
            "factory/operations data that Tally cannot see."
        )

    rule = _match_rule(context)
    apply_policy_defer = True
    if rule:
        mvp: list[str] = []
        for dt in rule["mvp_doctypes"]:
            if dt in template_set and dt not in mvp:
                mvp.append(dt)
        for pattern, dt in (rule.get("optional_if_mentioned") or {}).items():
            if re.search(pattern, context, re.I) and dt in template_set and dt not in mvp:
                mvp.append(dt)
        reasoning = rule["reasoning"]
        scoping_mode = f"bottleneck_{rule['id']}"
        # Bottleneck-scoped MVP overrides template defer_until_post_mvp for Day-1 plan
        apply_policy_defer = False
    else:
        # Fallback: full template minus policy deferrals
        mvp = [d for d in template_set if d not in policy_defer]
        reasoning = "No specific bottleneck rule matched; using template minus deferred modules."
        scoping_mode = "template_minus_defer"

    # always_ask modules must be in Day-1 MVP
    for dt in policy_always:
        if dt in template_set and dt not in mvp:
            mvp.append(dt)

    # Policy deferrals never in Day-1 (fallback mode only)
    if apply_policy_defer:
        mvp = [d for d in mvp if d not in policy_defer]

    # Tally bridge: skip finance-heavy master data unless bottleneck needs sales bridge
    if dual_system_note and "Sales Order" in mvp:
        finance_masters = {"Customer", "Supplier", "Quotation"}
        mvp = [d for d in mvp if d not in finance_masters or d == "Sales Order"]

    # Cap size (always_ask can push slightly over — trim optional last)
    if len(mvp) > _MAX_DAY1_SEEDS:
        required = [d for d in mvp if d in policy_always]
        rest = [d for d in mvp if d not in required]
        mvp = required + rest[: max(0, _MAX_DAY1_SEEDS - len(required))]

    deferred = [d for d in template_set if d not in mvp]
    if apply_policy_defer:
        for d in policy_defer:
            if d in mvp:
                mvp.remove(d)
            if d not in deferred and d in template_set:
                deferred.append(d)

    return {
        "mvp_seeds": mvp,
        "deferred_seeds": deferred,
        "scoping_mode": scoping_mode,
        "scoping_reasoning": reasoning,
        "dual_system_note": dual_system_note,
    }
