"""
Universal gate contracts for IS and OS (Company Brain v1.0.0).

See docs/v1.0.0/OPERATING_MODEL.md for gate semantics.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal, Optional

GateName = Literal["resolve", "complete", "clarify", "commit"]
GateStatus = Literal["ok", "needs_human", "blocked"]
GapSeverity = Literal["blocking", "choice", "hint"]


@dataclass
class GapItem:
    """A single human-facing gap at RESOLVE or COMPLETE."""

    field: str
    question: str
    severity: GapSeverity = "blocking"
    candidates: list[str] = field(default_factory=list)
    rule_id: Optional[str] = None
    doctype: Optional[str] = None
    entity_key: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GapItem:
        return cls(
            field=str(data.get("field") or ""),
            question=str(data.get("question") or ""),
            severity=data.get("severity") or "blocking",  # type: ignore[arg-type]
            candidates=list(data.get("candidates") or []),
            rule_id=data.get("rule_id"),
            doctype=data.get("doctype"),
            entity_key=data.get("entity_key"),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass
class HonestySlice:
    """Pass / partial / fail slice attached to a gate result."""

    valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    corrections: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HonestySlice:
        return cls(
            valid=bool(data.get("valid", True)),
            errors=list(data.get("errors") or []),
            warnings=list(data.get("warnings") or []),
            corrections=list(data.get("corrections") or []),
        )


@dataclass
class GateResult:
    """Standard return shape from RESOLVE, COMPLETE, CLARIFY, or COMMIT."""

    gate: GateName
    status: GateStatus
    resolved: dict[str, Any] = field(default_factory=dict)
    gaps: list[GapItem] = field(default_factory=list)
    honesty: HonestySlice = field(default_factory=HonestySlice)
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "gate": self.gate,
            "status": self.status,
            "resolved": self.resolved,
            "gaps": [g.to_dict() for g in self.gaps],
            "honesty": self.honesty.to_dict(),
            "meta": self.meta,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GateResult:
        gaps_raw = data.get("gaps") or []
        gaps = [
            g if isinstance(g, GapItem) else GapItem.from_dict(g)
            for g in gaps_raw
        ]
        honesty_raw = data.get("honesty") or {}
        honesty = (
            honesty_raw
            if isinstance(honesty_raw, HonestySlice)
            else HonestySlice.from_dict(honesty_raw)
        )
        return cls(
            gate=data["gate"],  # type: ignore[arg-type]
            status=data["status"],  # type: ignore[arg-type]
            resolved=dict(data.get("resolved") or {}),
            gaps=gaps,
            honesty=honesty,
            meta=dict(data.get("meta") or {}),
        )


def gap_to_clarification_question(gap: GapItem) -> str:
    """Plain-language question for UI / supervisor."""
    if gap.question.strip():
        return gap.question.strip()
    if gap.candidates:
        preview = ", ".join(gap.candidates[:5])
        more = len(gap.candidates) - 5
        suffix = f" (and {more} more)" if more > 0 else ""
        return f"Which {gap.field} did you mean? Options: {preview}{suffix}"
    return f"Please provide {gap.field}."


def gate_result_ok(
    gate: GateName,
    resolved: Optional[dict[str, Any]] = None,
    *,
    meta: Optional[dict[str, Any]] = None,
) -> GateResult:
    return GateResult(
        gate=gate,
        status="ok",
        resolved=resolved or {},
        meta=meta or {},
    )


def gate_result_needs_human(
    gate: GateName,
    gaps: list[GapItem],
    *,
    resolved: Optional[dict[str, Any]] = None,
    meta: Optional[dict[str, Any]] = None,
) -> GateResult:
    return GateResult(
        gate=gate,
        status="needs_human",
        resolved=resolved or {},
        gaps=gaps,
        meta=meta or {},
    )


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
