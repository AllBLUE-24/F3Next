"""Tests for structural assurance tiers."""

from __future__ import annotations

from pathlib import Path

from containers.discovery.discovery_assurance import compute_assurance

FIXTURES = Path(__file__).parent / "fixtures"
YIELD_TRANSCRIPT = (FIXTURES / "cleaning_chemicals_yield.txt").read_text(encoding="utf-8")


def test_green_when_valid_with_strong_signals():
    transcript = (
        YIELD_TRANSCRIPT
        + " We operate from a single factory site. Fiscal year is April to March. "
        "Opening stock cutover is 1 April. Single company in INR."
    )
    result = compute_assurance(
        transcript=transcript,
        niche_id="manufacturing_project_chemical",
        validation={"valid": True, "issues": [], "promoted_doctypes": ["Job Card"]},
        coverage={
            "industry": {"value": "chemicals"},
            "pain_point": {"value": "yield"},
            "legacy_system": {"value": "Tally"},
        },
        clarification_complete=True,
        closure_test="After Day-1 we can answer yield variance per batch because Job Card captures consumption.",
        niche_resolution_source="planner",
        template_available=True,
    )
    assert result.level == "green"
    assert result.validator_valid


def test_yellow_when_closure_test_missing():
    result = compute_assurance(
        transcript=YIELD_TRANSCRIPT,
        niche_id="manufacturing_project_chemical",
        validation={"valid": True, "issues": [], "promoted_doctypes": []},
        clarification_complete=True,
        closure_test="",
    )
    assert result.level == "yellow"
    assert any("closure test" in r.lower() for r in result.reasons)


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


def test_yellow_on_offline_planner_fallback():
    result = compute_assurance(
        transcript=YIELD_TRANSCRIPT,
        niche_id="manufacturing_project_chemical",
        validation={"valid": True, "issues": [], "promoted_doctypes": []},
        clarification_complete=True,
        closure_test="Closure ok.",
        niche_resolution_source="planner_offline_fallback",
    )
    assert result.level == "yellow"
    assert any("offline fallback" in r.lower() for r in result.reasons)


def test_yellow_when_f3iche_template_missing():
    result = compute_assurance(
        transcript=YIELD_TRANSCRIPT,
        niche_id="trading_fmcg_distributor",
        validation={"valid": True, "issues": [], "promoted_doctypes": []},
        clarification_complete=True,
        closure_test="Closure ok.",
        template_available=False,
    )
    assert result.level == "yellow"
    assert any("template" in r.lower() for r in result.reasons)


def test_yellow_when_clarification_incomplete():
    result = compute_assurance(
        transcript=YIELD_TRANSCRIPT,
        niche_id="manufacturing_project_chemical",
        validation={"valid": True, "issues": [], "promoted_doctypes": []},
        clarification_complete=False,
    )
    assert result.level == "yellow"
    assert any("clarifying" in r.lower() for r in result.reasons)
