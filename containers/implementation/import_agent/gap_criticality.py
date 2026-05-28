"""
Gap criticality helpers — align import plan blocking with data readiness tiers.
"""
from __future__ import annotations

from typing import Any, Dict, Optional


def criticality_from_phase(phase: Optional[str]) -> str:
    """Match data_readiness_agent.activities._criticality_from_phase."""
    phase_l = (phase or "").lower()
    if phase_l.startswith("phase_a") or phase_l.startswith("phase_b"):
        return "critical"
    if phase_l.startswith("phase_c"):
        return "non_critical"
    return "optional"


def build_doctype_criticality_map(readiness_row: Any) -> Dict[str, str]:
    """Build {doctype: criticality} from ISDataReadinessAssessment JSONB columns."""
    out: Dict[str, str] = {}
    if not readiness_row:
        return out

    for bucket_name in ("missing_doctypes", "partial_doctypes"):
        bucket = getattr(readiness_row, bucket_name, None) or []
        for item in bucket:
            if not isinstance(item, dict):
                continue
            dt = str(item.get("doctype") or "").strip()
            if not dt:
                continue
            crit = str(item.get("criticality") or "").strip().lower()
            if not crit:
                crit = criticality_from_phase(item.get("phase"))
            out[dt] = crit
    return out


def gap_criticality(
    doctype: str,
    phase_id: str,
    criticality_map: Dict[str, str],
) -> str:
    from containers.implementation.is_common.doctype_resolver import resolve_doctype

    canonical = resolve_doctype(doctype)
    if canonical in criticality_map:
        return criticality_map[canonical]
    if doctype in criticality_map:
        return criticality_map[doctype]
    return criticality_from_phase(phase_id)


def is_blocking_gap(criticality: str) -> bool:
    """Only critical gaps block live import."""
    return str(criticality or "").lower() == "critical"
