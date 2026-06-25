"""MVP import scope — finalize blocking aligns with bottleneck seeds, not full graph."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple

from containers.implementation.is_common.doctype_resolver import resolve_doctype
from containers.implementation.import_agent.gap_criticality import gap_criticality, is_blocking_gap

# Site setup / baseline — never block import when unmapped in plan.
_ALWAYS_OPTIONAL = frozenset({
    "Company",
    "Warehouse",
    "UOM",
    "Chart of Accounts",
    "Account",
    "Cost Center",
    "Fiscal Year",
    "Currency",
    "Tax Template",
})

# Link masters deferred when not uploaded (golden matrix §6; stubs at import).
_LINK_OPTIONAL = frozenset({"Project", "Item"})


def parse_mvp_scope_from_target(target_data: Optional[Dict[str, Any]]) -> Tuple[Set[str], Set[str]]:
    """Return (mvp_seed_doctypes, deferred_doctypes) from target_structure R2 JSON."""
    if not target_data:
        return set(), set()
    seeds = {
        resolve_doctype(str(s))
        for s in (target_data.get("seed_doctypes") or [])
        if str(s or "").strip()
    }
    deferred = {
        resolve_doctype(str(s))
        for s in (target_data.get("deferred_doctypes") or [])
        if str(s or "").strip()
    }
    return seeds, deferred


def is_out_of_mvp_scope(
    doctype: str,
    mvp_seeds: Set[str],
    deferred: Set[str],
) -> bool:
    """True when an unmapped plan step should not block live import."""
    canonical = resolve_doctype(doctype or "")
    if canonical in _ALWAYS_OPTIONAL or canonical in _LINK_OPTIONAL:
        return True
    if canonical in deferred:
        return True
    if mvp_seeds and canonical not in mvp_seeds:
        return True
    return False


def blocks_import_when_unmapped(
    doctype: str,
    mvp_seeds: Set[str],
    deferred: Set[str],
    criticality_map: Dict[str, str],
    phase_id: str,
) -> bool:
    """True when unmapped doctype is in MVP scope and critical enough to block."""
    if is_out_of_mvp_scope(doctype, mvp_seeds, deferred):
        return False
    crit = gap_criticality(doctype, phase_id, criticality_map)
    return is_blocking_gap(crit)


def blocking_unmapped_seeds(
    seed_doctypes: List[str],
    mapped_doctypes: Set[str],
    deferred: Set[str],
) -> List[str]:
    """MVP seeds with no mapped rows that would block finalize/import."""
    mvp_seeds = {resolve_doctype(str(s)) for s in seed_doctypes if str(s or "").strip()}
    out: List[str] = []
    for raw in seed_doctypes:
        canonical = resolve_doctype(str(raw))
        if canonical in mapped_doctypes:
            continue
        if is_out_of_mvp_scope(canonical, mvp_seeds, deferred):
            continue
        out.append(str(raw))
    return out
