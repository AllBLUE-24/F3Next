"""
Deterministic quality gate evaluation — primary path without LLM latency.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from shared.models.quality_gate import QualityGateResult, StepContract

_PIPELINE_BUG_PATTERNS = re.compile(
    r"(internal|traceback|graph|corpus_merge|ler|schema resolver|kb miss|pipeline)",
    re.I,
)
_USER_DATA_PATTERNS = re.compile(
    r"(empty|missing|required|no source column|identity|user must|upload)",
    re.I,
)
_AUTO_FIX_PATTERNS = re.compile(
    r"(enum|naming_series|default|strip unit|normaliz|kb default|format)",
    re.I,
)


def _error_texts(node_status: Dict[str, Any]) -> List[str]:
    texts: List[str] = []
    for err in node_status.get("errors") or []:
        if isinstance(err, dict):
            texts.append(str(err.get("message") or err.get("detail") or err))
        else:
            texts.append(str(err))
    primary = node_status.get("primary_result")
    if isinstance(primary, dict):
        for e in primary.get("errors") or []:
            texts.append(str(e))
    return texts


def _warning_texts(node_status: Dict[str, Any]) -> List[str]:
    texts: List[str] = []
    for w in node_status.get("warnings") or []:
        if isinstance(w, dict):
            texts.append(str(w.get("message") or w))
        else:
            texts.append(str(w))
    return texts


def evaluate_quality_gate(
    contract: StepContract,
    node_report: Dict[str, Any],
    *,
    retry_count: int = 0,
) -> Optional[QualityGateResult]:
    """
    Rule-based gate. Returns None when LLM review is recommended (ambiguous).
    """
    node_status = node_report.get("node_status") or {}
    actual = node_report.get("actual_outputs") or {}
    status = str(node_status.get("status") or actual.get("status") or "")
    errors = _error_texts(node_status)
    warnings = _warning_texts(node_status)
    missing = node_status.get("missing_information") or []
    combined = " ".join(errors + warnings).lower()

    # Step-specific outputs (IS classify / map / plan / import)
    if actual.get("plan_status") == "blocked":
        return QualityGateResult(
            verdict="hard_block",
            analysis="Import plan is blocked due to critical gaps.",
            user_gap_description="Resolve validation failures or upload missing files before import.",
        )
    if actual.get("plan_status") in ("ready", "ready_with_gaps"):
        return QualityGateResult(
            verdict="ok",
            analysis=f"Import plan status: {actual.get('plan_status')}.",
        )

    mapped = actual.get("mapped_count")
    total = actual.get("total_files")
    if mapped is not None and total is not None and total > 0 and mapped == 0:
        return QualityGateResult(
            verdict="user_gap",
            analysis="No files were mapped successfully.",
            user_gap_description="Upload recognizable tabular files or clarify doctype mapping in chat.",
        )

    phase_result = actual.get("result")
    if isinstance(phase_result, dict) and phase_result.get("steps_failed", 0) > 0:
        return QualityGateResult(
            verdict="user_gap",
            analysis="Import phase had failed steps.",
            user_gap_description=(
                f"Phase {actual.get('phase_label', '?')}: "
                f"{phase_result.get('steps_failed')} step(s) failed."
            ),
        )

    if actual.get("assignment_count") == 0 and contract.step_name == "assign_corpus_doctypes":
        return QualityGateResult(
            verdict="user_gap",
            analysis="No corpus doctype assignments produced.",
            user_gap_description="Upload files with recognizable columns or describe file types in chat.",
        )

    conflicts = actual.get("source_file_conflicts") or []
    if conflicts and contract.step_name == "validate_mapped_data":
        first = conflicts[0] if isinstance(conflicts[0], dict) else {}
        return QualityGateResult(
            verdict="user_gap",
            analysis="Source filename implies a different doctype than assigned.",
            user_gap_description=(
                f"File '{first.get('file', '?')}' may belong to "
                f"{first.get('implied_doctype', '?')} not {first.get('assigned_doctype', '?')}."
            ),
        )

    if contract.step_name == "validate_mapped_data":
        checks = actual.get("checks") or []
        if isinstance(checks, list):
            for check in checks:
                if not isinstance(check, dict):
                    continue
                errs = check.get("errors") or []
                if any("empty required value" in str(e).lower() for e in errs):
                    return QualityGateResult(
                        verdict="user_gap",
                        analysis="Row-level empty identity or required values detected.",
                        user_gap_description=str(errs[0])[:300] if errs else None,
                    )

    # OS validate_payload shape
    if "valid" in actual:
        if actual.get("valid") is True:
            return QualityGateResult(
                verdict="ok",
                analysis="Payload validation passed.",
            )
        os_errors = actual.get("errors") or []
        if os_errors and _AUTO_FIX_PATTERNS.search(combined) and retry_count < contract.max_retries:
            return QualityGateResult(
                verdict="retry",
                analysis="Validation errors look auto-correctable.",
                retry_feedback="; ".join(
                    str(e.get("message", e)) for e in os_errors[:3] if isinstance(e, dict)
                ),
                auto_corrections=list(actual.get("auto_corrections") or []),
            )
        if os_errors:
            return QualityGateResult(
                verdict="user_gap",
                analysis="Validation failed; user input required.",
                user_gap_description="; ".join(
                    str(e.get("message", e)) for e in os_errors[:3] if isinstance(e, dict)
                ),
            )

    # IS success
    if status == "success" and not errors:
        return QualityGateResult(verdict="ok", analysis="Step completed successfully.")

    # IS partial — data warnings only
    if status == "partial" and not errors:
        return QualityGateResult(
            verdict="ok",
            analysis="Partial pass with warnings only (data quality, not pipeline failure).",
        )

    # Explicit missing information → user gap
    if missing:
        return QualityGateResult(
            verdict="user_gap",
            analysis="Missing information requires user input.",
            user_gap_description="; ".join(str(m) for m in missing[:5]),
        )

    if errors:
        if _PIPELINE_BUG_PATTERNS.search(combined):
            if retry_count < contract.max_retries and _AUTO_FIX_PATTERNS.search(combined):
                return QualityGateResult(
                    verdict="retry",
                    analysis="Pipeline issue may be recoverable via auto-fix.",
                    retry_feedback=combined[:500],
                )
            return QualityGateResult(
                verdict="hard_block",
                analysis="Pipeline or KB failure detected.",
                user_gap_description=errors[0][:300] if errors else None,
            )

        if _USER_DATA_PATTERNS.search(combined):
            return QualityGateResult(
                verdict="user_gap",
                analysis="Data gap requires user-supplied values or files.",
                user_gap_description=errors[0][:300] if errors else None,
            )

        if _AUTO_FIX_PATTERNS.search(combined) and retry_count < contract.max_retries:
            return QualityGateResult(
                verdict="retry",
                analysis="Errors appear auto-fixable (defaults, enum, format).",
                retry_feedback=errors[0][:300] if errors else combined[:300],
            )

        return QualityGateResult(
            verdict="user_gap",
            analysis="Unresolved validation issues.",
            user_gap_description=errors[0][:300] if errors else None,
        )

    if status == "failed":
        return QualityGateResult(
            verdict="hard_block",
            analysis=f"Step failed with status={status}.",
        )

    return None
