"""Validation gate for Step 4."""
from __future__ import annotations

from typing import Any, Dict, List

from containers.implementation.map_validate.config import block_import_on_fail
from containers.implementation.map_validate.models import ValidationLevel


def compute_validation_level(report: Dict[str, Any]) -> ValidationLevel:
    overall = str(report.get("overall") or "partial").lower()
    if overall == "fail":
        return "fail"
    if overall == "partial":
        return "partial"
    if report.get("warnings"):
        return "partial"
    return "pass"


def compute_import_ready(
    validation_level: ValidationLevel,
    *,
    map_results: List[Any],
    blocking_unmapped_seeds: List[str] | None = None,
    open_critical_gaps: int = 0,
) -> bool:
    if open_critical_gaps > 0:
        return False
    if blocking_unmapped_seeds:
        return False
    if block_import_on_fail() and validation_level == "fail":
        return False
    if not any(getattr(r, "passed", False) or (isinstance(r, dict) and r.get("passed")) for r in map_results):
        return False
    return validation_level in ("pass", "partial")


def gate_summary(
    level: ValidationLevel,
    *,
    error_count: int,
    warning_count: int,
    mapped_doctypes: List[str],
) -> str:
    if level == "pass":
        return (
            f"Mapped data for {len(mapped_doctypes)} module(s) passed validation. "
            "You can confirm and proceed to import."
        )
    if level == "partial":
        return (
            f"Mapped data validated with {warning_count} warning(s). "
            "Review highlighted rows before importing."
        )
    return (
        f"{error_count} blocking validation error(s) must be fixed before import."
    )
