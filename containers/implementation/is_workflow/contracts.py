"""Fail-closed progression predicates for the implementation workflow."""

from __future__ import annotations

from typing import Any, Mapping


def readiness_blocks_progress(
    envelope_status: str,
    assessment: Mapping[str, Any] | None,
) -> bool:
    if envelope_status == "failed":
        return True
    return not bool(
        (assessment or {}).get("minimum_viable_import_possible", False)
    )


def mapping_blocks_progress(mapped_count: int, total_files: int) -> bool:
    return total_files <= 0 or mapped_count <= 0


def import_phase_failed(result: Any) -> bool:
    if not isinstance(result, dict):
        return True
    return result.get("status") == "error" or int(result.get("steps_failed") or 0) > 0
