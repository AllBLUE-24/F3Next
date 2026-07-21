"""Tests for structural assurance tiers."""

from __future__ import annotations

from pathlib import Path

from containers.discovery.discovery_assurance import compute_assurance

FIXTURES = Path(__file__).parent / "fixtures"
YIELD_TRANSCRIPT = (FIXTURES / "cleaning_chemicals_yield.txt").read_text(encoding="utf-8")


def test_green_when_valid_with_strong_signals():
    result = compute_assurance(
        transcript=YIELD_TRANSCRIPT,
        niche_id="manufacturing_project_chemical",
        validation={"valid": True, "issues": [], "promoted_doctypes": ["Job Card"]},
        coverage={
            "industry": {"value": "chemicals"},
            "pain_point": {"value": "yield"},
            "legacy_system": {"value": "Tally"},
        },
        clarification_complete=True,
    )
    assert result.level == "green"
    assert result.validator_valid


def test_red_on_validation_errors():
    result = compute_assurance(
        transcript=YIELD_TRANSCRIPT,
        niche_id="manufacturing_project_chemical",
        validation={
            "valid": False,
            "issues": [{"severity": "error", "message": "Missing BOM for manufacturing"}],
            "promoted_doctypes": [],
        },
    )
    assert result.level == "red"
    assert "Missing BOM" in result.reasons[0]


def test_yellow_on_many_promotions():
    result = compute_assurance(
        transcript=YIELD_TRANSCRIPT,
        niche_id="manufacturing_project_chemical",
        validation={
            "valid": True,
            "issues": [],
            "promoted_doctypes": ["Job Card", "Stock Entry", "Workstation"],
        },
        clarification_complete=True,
    )
    assert result.level == "yellow"
    assert any("promoted" in r.lower() for r in result.reasons)


def test_yellow_when_clarification_incomplete():
    result = compute_assurance(
        transcript=YIELD_TRANSCRIPT,
        niche_id="manufacturing_project_chemical",
        validation={"valid": True, "issues": [], "promoted_doctypes": []},
        clarification_complete=False,
    )
    assert result.level == "yellow"
    assert any("clarifying" in r.lower() for r in result.reasons)
