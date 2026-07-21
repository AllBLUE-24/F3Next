"""
Discovery Step 1 — structural assurance tiers (GREEN / YELLOW / RED).

Not LLM confidence — computed from validator output, signal margin, and promotions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from containers.discovery.archetype_registry import signal_match_rankings

AssuranceLevel = Literal["green", "yellow", "red"]


@dataclass
class AssuranceResult:
    level: AssuranceLevel
    reasons: list[str] = field(default_factory=list)
    signal_top_score: int = 0
    signal_margin: int = 0
    promotion_count: int = 0
    validator_valid: bool = True
    warning_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "level": self.level,
            "reasons": self.reasons,
            "signal_top_score": self.signal_top_score,
            "signal_margin": self.signal_margin,
            "promotion_count": self.promotion_count,
            "validator_valid": self.validator_valid,
            "warning_count": self.warning_count,
        }


def compute_assurance(
    *,
    transcript: str,
    niche_id: str,
    validation: dict[str, Any],
    coverage: dict[str, Any] | None = None,
    clarification_complete: bool = True,
) -> AssuranceResult:
    reasons: list[str] = []
    rankings = signal_match_rankings(transcript, niche_id, top_k=2, min_score=1)
    top_score = rankings[0]["score"] if rankings else 0
    second_score = rankings[1]["score"] if len(rankings) > 1 else 0
    margin = top_score - second_score

    promoted = validation.get("promoted_doctypes") or []
    promotion_count = len(promoted)
    issues = validation.get("issues") or []
    errors = [i for i in issues if i.get("severity") == "error"]
    warnings = [i for i in issues if i.get("severity") == "warning"]
    valid = validation.get("valid", True)

    if not valid or errors:
        return AssuranceResult(
            level="red",
            reasons=[e.get("message", "Validation failed") for e in errors] or ["Validation failed"],
            signal_top_score=top_score,
            signal_margin=margin,
            promotion_count=promotion_count,
            validator_valid=valid,
            warning_count=len(warnings),
        )

    level: AssuranceLevel = "green"

    if top_score < 2 or margin < 1:
        level = "yellow"
        reasons.append("Weak archetype signal match — plan based on general manufacturing patterns.")

    if promotion_count > 2:
        level = "yellow"
        reasons.append(
            f"Validator promoted {promotion_count} modules beyond the initial draft — review promoted items."
        )

    if warnings:
        level = "yellow"
        for w in warnings[:2]:
            reasons.append(w.get("message", "Validator warning"))

    if not clarification_complete:
        level = "yellow"
        reasons.append("Clarifying questions were skipped or incomplete.")

    cov = coverage or {}
    missing_dims = [
        dim for dim in ("industry", "pain_point", "legacy_system")
        if not (cov.get(dim) or {}).get("value")
    ]
    if len(missing_dims) >= 2:
        level = "yellow"
        reasons.append(f"Limited coverage extraction: missing {', '.join(missing_dims)}.")

    if level == "green":
        reasons.append("Structural closure passed with strong signal match.")

    return AssuranceResult(
        level=level,
        reasons=reasons,
        signal_top_score=top_score,
        signal_margin=margin,
        promotion_count=promotion_count,
        validator_valid=valid,
        warning_count=len(warnings),
    )


__all__ = ["AssuranceResult", "AssuranceLevel", "compute_assurance"]
