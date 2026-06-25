"""Canonical IS import phase execution order (dependency-aware)."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

# Projects must exist before transactional docs that link to Project (Sales Order, etc.).
PHASE_EXECUTION_ORDER: tuple[str, ...] = (
    "phase_0_site_config",
    "phase_a_config",
    "phase_b_master",
    "phase_d_projects",
    "phase_c_transactional",
)


def sort_phases(phases: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any]]]:
    rank = {phase_id: idx for idx, phase_id in enumerate(PHASE_EXECUTION_ORDER)}
    return sorted(
        phases.items(),
        key=lambda item: (rank.get(item[0], 999), item[0]),
    )
