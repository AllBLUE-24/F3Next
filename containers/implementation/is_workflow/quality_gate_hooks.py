"""
Helpers for IS workflow quality gate integration (imported via pass_through).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from shared.models.is_status import NodeStatusEnvelope

_ENVELOPE_FIELDS = frozenset({
    "status",
    "primary_result",
    "errors",
    "warnings",
    "missing_information",
    "conflicts",
})
_STATUS_ALIASES = {
    "error": "failed",
    "fail": "failed",
    "failed": "failed",
    "partial": "partial",
    "success": "success",
    "passed": "success",
    "ready": "success",
    "ready_with_gaps": "partial",
    "blocked": "failed",
}


def _normalize_node_status(raw: Any) -> str:
    key = str(raw or "").strip().lower()
    mapped = _STATUS_ALIASES.get(key, key)
    if mapped in ("success", "partial", "failed"):
        return mapped
    return "failed"


def coerce_envelope(env: Any, *, fallback_primary: Optional[Dict] = None) -> NodeStatusEnvelope:
    if isinstance(env, NodeStatusEnvelope):
        return env
    if isinstance(env, dict):
        if "status" in env:
            primary = dict(env.get("primary_result") or {})
            for key, value in env.items():
                if key not in _ENVELOPE_FIELDS:
                    primary[key] = value
            if fallback_primary:
                primary = {**fallback_primary, **primary}
            return NodeStatusEnvelope(
                status=_normalize_node_status(env.get("status")),  # type: ignore[arg-type]
                primary_result=primary or None,
                errors=list(env.get("errors") or []),
                warnings=list(env.get("warnings") or []),
                missing_information=list(env.get("missing_information") or []),
                conflicts=list(env.get("conflicts") or []),
            )
        return NodeStatusEnvelope.success(primary_result=env)
    if isinstance(env, str):
        if env in ("passed", "success", "ready", "ready_with_gaps"):
            return NodeStatusEnvelope.success(primary_result={"status": env})
        return NodeStatusEnvelope.failed(primary_result={"status": env})
    return NodeStatusEnvelope.success(primary_result=fallback_primary or {})


def mapping_summary_envelope(
    mapped_count: int,
    total_files: int,
    failures: Optional[List[str]] = None,
) -> NodeStatusEnvelope:
    failures = failures or []
    primary = {
        "mapped_count": mapped_count,
        "total_files": total_files,
        "failures": failures[:10],
    }
    if mapped_count == 0 and total_files > 0:
        return NodeStatusEnvelope.failed(
            primary_result=primary,
            errors=[{"message": "No files mapped successfully"}],
        )
    if failures:
        return NodeStatusEnvelope.partial(
            primary_result=primary,
            warnings=[{"message": f} for f in failures[:5]],
        )
    return NodeStatusEnvelope.success(primary_result=primary)
