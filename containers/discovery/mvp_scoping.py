"""
Bottleneck-driven MVP seed scoping for Discovery Assistant Step 1.

Narrows f3iche template seeds to Day-1 MVP using Research archetypes (F3iche
bottlenecks[] + discovery/kb/archetype_catalog.json). Legacy regex rules are
opt-in via DISCOVERY_USE_LEGACY_REGEX_SCOPING.
"""

from __future__ import annotations

import os
import re
from typing import Any, Optional

from containers.discovery.archetype_registry import (
    best_signal_match,
    canonicalize_seed,
    get_by_id,
    resolve_seed_doctypes,
)

_USE_LEGACY_REGEX = os.getenv("DISCOVERY_USE_LEGACY_REGEX_SCOPING", "false").lower() in (
    "1",
    "true",
    "yes",
)

_MAX_DAY1_SEEDS = 8

# Legacy regex rules — deprecated; enable only for rollback
_LEGACY_SCOPING_RULES: list[dict[str, Any]] = [
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

_FINANCE_MASTERS = frozenset({"Customer", "Supplier", "Quotation"})


def _combined_context(
    *,
    mvp_focus: dict[str, Any] | None,
    coverage: dict[str, Any] | None,
    chat_transcript: str,
) -> str:
    parts: list[str] = []
    if mvp_focus:
        parts.append(str(mvp_focus.get("primary_bottleneck") or ""))
        if mvp_focus.get("archetype_id"):
            parts.append(str(mvp_focus["archetype_id"]))
        for req in mvp_focus.get("functional_requirements") or []:
            parts.append(str(req))
    if coverage:
        for key in ("pain_point", "legacy_system", "strategy", "industry", "scale"):
            entry = coverage.get(key) or {}
            if entry.get("value"):
                parts.append(str(entry["value"]))
    parts.append(chat_transcript or "")
    return " ".join(parts).lower()


def _legacy_accounting_system(coverage: dict[str, Any] | None) -> str:
    if not coverage:
        return ""
    legacy = coverage.get("legacy_system") or {}
    return str(legacy.get("value") or "").lower()


def _policy_doctype_names(policy_values: set[str], template_set: set[str]) -> set[str]:
    """import_field_policy lists fields; only treat values that are template doctypes."""
    return {v for v in policy_values if v in template_set}


def _match_legacy_rule(context: str) -> dict[str, Any] | None:
    for rule in _LEGACY_SCOPING_RULES:
        if any(re.search(p, context, re.I) for p in rule["patterns"]):
            return rule
    return None


def _apply_legacy_rule(rule: dict[str, Any], template_set: list[str], context: str) -> list[str]:
    mvp: list[str] = []
    for dt in rule["mvp_doctypes"]:
        if dt in template_set and dt not in mvp:
            mvp.append(dt)
    for pattern, dt in (rule.get("optional_if_mentioned") or {}).items():
        if re.search(pattern, context, re.I) and dt in template_set and dt not in mvp:
            mvp.append(dt)
    return mvp


def _seeds_from_archetype(
    archetype: dict[str, Any],
    template_seeds: list[str],
) -> tuple[list[str], list[str], str, str]:
    seeds, graph_extensions = resolve_seed_doctypes(archetype, template_seeds)
    mode_suffix = str(archetype.get("archetype_id") or "unknown")
    if graph_extensions:
        mode = f"archetype_{mode_suffix}_graph_extension"
    else:
        mode = f"archetype_{mode_suffix}"
    reasoning = (
        str(archetype.get("primary_bottleneck") or "").strip()
        or f"Day-1 MVP scoped to archetype {mode_suffix}."
    )
    return seeds, graph_extensions, mode, reasoning


def _apply_dual_system_filter(
    mvp: list[str],
    *,
    dual_system_note: str,
    archetype: dict[str, Any] | None,
) -> list[str]:
    if not dual_system_note:
        return mvp
    hint_seeds = {
        canonicalize_seed(str(h))
        for h in (archetype.get("day1_seed_hints") or [] if archetype else [])
    }
    required_finance = hint_seeds & _FINANCE_MASTERS
    if required_finance:
        return mvp
    if "Sales Order" in mvp and "Customer" not in hint_seeds:
        return [d for d in mvp if d not in _FINANCE_MASTERS or d == "Sales Order"]
    return [d for d in mvp if d not in _FINANCE_MASTERS]


def _cap_seeds(mvp: list[str], *, priority: list[str], max_seeds: int) -> list[str]:
    if len(mvp) <= max_seeds:
        return mvp
    ordered = [d for d in priority if d in mvp]
    for d in mvp:
        if d not in ordered:
            ordered.append(d)
    return ordered[:max_seeds]


def _minimal_fallback_seeds(template_seeds: list[str]) -> list[str]:
    if "Item" in template_seeds:
        return ["Item"]
    return template_seeds[:1] if template_seeds else []


def scope_mvp_seeds(
    *,
    template_seeds: list[str],
    f3iche_id: Optional[str] = None,
    f3iche_data: dict[str, Any] | None = None,
    mvp_focus: dict[str, Any] | None = None,
    coverage: dict[str, Any] | None = None,
    chat_transcript: str = "",
    user_confirmed_override: list[str] | None = None,
) -> dict[str, Any]:
    """
    Return bottleneck-scoped Day-1 seeds and deferred modules.

    Priority: user override → archetype_id → signal match → legacy regex (flag)
    → minimal fallback.
    """
    template_set = list(dict.fromkeys(template_seeds))
    template_set_lookup = set(template_set)

    policy = (f3iche_data or {}).get("import_field_policy") or {}
    policy_defer = _policy_doctype_names(set(policy.get("defer_until_post_mvp") or []), template_set_lookup)
    policy_always = _policy_doctype_names(set(policy.get("always_ask") or []), template_set_lookup)

    if user_confirmed_override:
        confirmed = [d for d in user_confirmed_override if d in template_set_lookup]
        deferred = [d for d in template_set if d not in confirmed]
        return {
            "mvp_seeds": confirmed,
            "deferred_seeds": deferred,
            "scoping_mode": "user_confirmed",
            "scoping_reasoning": "User confirmed module selection.",
            "dual_system_note": "",
            "archetype_id": None,
            "archetype_source": None,
            "signal_match_score": None,
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

    archetype: dict[str, Any] | None = None
    archetype_source: str | None = None
    signal_match_score: int | None = None
    graph_extensions: list[str] = []

    archetype_id = (mvp_focus or {}).get("archetype_id")
    if archetype_id:
        archetype = get_by_id(str(archetype_id), f3iche_id)
        if archetype:
            archetype_source = "mvp_focus"

    if not archetype:
        signal_hit = best_signal_match(context, f3iche_id)
        if signal_hit:
            archetype, signal_match_score = signal_hit
            archetype_source = "signal_match"

    if archetype:
        mvp, graph_extensions, scoping_mode, reasoning = _seeds_from_archetype(archetype, template_set)
        if not mvp:
            mvp = _minimal_fallback_seeds(template_set)
            scoping_mode = "archetype_empty_fallback"
            reasoning = (
                f"Archetype {archetype.get('archetype_id')} had no resolvable seeds; "
                "using minimal operational default."
            )
    elif _USE_LEGACY_REGEX:
        rule = _match_legacy_rule(context)
        if rule:
            mvp = _apply_legacy_rule(rule, template_set, context)
            scoping_mode = f"legacy_regex_{rule['id']}"
            reasoning = rule["reasoning"]
            archetype = get_by_id(rule["id"], f3iche_id)
        else:
            mvp = _minimal_fallback_seeds(template_set)
            scoping_mode = "minimal_fallback"
            reasoning = "No archetype matched; using minimal Day-1 operational default."
    else:
        mvp = _minimal_fallback_seeds(template_set)
        scoping_mode = "minimal_fallback"
        reasoning = "No archetype matched; using minimal Day-1 operational default."

    for dt in policy_always:
        if dt in template_set_lookup and dt not in mvp:
            mvp.append(dt)

    mvp = _apply_dual_system_filter(mvp, dual_system_note=dual_system_note, archetype=archetype)

    priority = list(mvp)
    mvp = _cap_seeds(mvp, priority=priority, max_seeds=_MAX_DAY1_SEEDS)

    deferred = [d for d in template_set if d not in mvp]

    return {
        "mvp_seeds": mvp,
        "deferred_seeds": deferred,
        "scoping_mode": scoping_mode,
        "scoping_reasoning": reasoning,
        "dual_system_note": dual_system_note,
        "archetype_id": (archetype or {}).get("archetype_id") or archetype_id,
        "archetype_source": archetype_source,
        "signal_match_score": signal_match_score,
        "graph_extensions": graph_extensions,
    }
