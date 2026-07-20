"""
V1-worthiness tests — offline planner draft + validator + build_target on dummy inputs.

No LLM credentials required. Proves validator fixes classifier gaps (e.g. Apex Resins).
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from containers.discovery.mvp_plan_draft import finalize_offline_mvp_plan
from containers.discovery.niche_resolver import resolve_discovery_f3iche_niche
from containers.discovery.target.build_target import build_discovery_target

_FIXTURES = Path(__file__).parent / "fixtures"
_MATRIX = _FIXTURES / "planner_v1_worthiness.json"


def _load_cases() -> list[dict]:
    if not _MATRIX.exists():
        return []
    data = json.loads(_MATRIX.read_text(encoding="utf-8"))
    return list(data.get("cases") or [])


def _case_id(case: dict) -> str:
    return str(case.get("id") or case.get("name"))


@pytest.mark.golden
@pytest.mark.parametrize("case", _load_cases(), ids=_case_id)
def test_planner_v1_worthiness_offline(case: dict):
    fixture = _FIXTURES / case["fixture"]
    transcript = fixture.read_text(encoding="utf-8").strip()
    coverage = case.get("coverage") or {}

    offline = finalize_offline_mvp_plan(
        transcript=transcript,
        coverage=coverage,
        industry=str((coverage.get("industry") or {}).get("value") or ""),
    )

    expect = case.get("expect") or {}

    niche = offline["f3iche_niche"]
    if expect.get("niche_id"):
        assert niche == expect["niche_id"], f"got niche {niche}"
    if expect.get("niche_not"):
        assert niche not in expect["niche_not"], f"wrong niche {niche}"

    validation = offline["validation"]
    assert validation["valid"] is True, validation.get("issues")

    day1 = offline["day1_doctypes"]
    for dt in expect.get("must_include") or []:
        assert dt in day1, f"expected {dt} in day1, got {day1}"

    for dt in expect.get("must_exclude") or []:
        assert dt not in day1, f"expected {dt} excluded, got {day1}"

    if expect.get("must_promote"):
        promoted = set(offline.get("promoted_doctypes") or [])
        for dt in expect["must_promote"]:
            assert dt in day1, f"{dt} should be in day1 after promotion"
            # promoted list may be empty if planner already included it
            assert dt in day1 or dt in promoted

    target = asyncio.run(
        build_discovery_target(
            f3iche=niche,
            mvp_focus=offline["mvp_focus"],
            coverage=coverage,
            chat_transcript=transcript,
        )
    )
    assert target["mvp_boundary"]["mode"] == "planner_validated"
    seeds = target["seed_doctypes"]
    for dt in expect.get("must_include") or []:
        assert dt in seeds, f"build_target missing {dt}, got {seeds}"


def test_apex_resins_offline_niche_not_jobshop():
    transcript = (_FIXTURES / "apex_resins_recall.txt").read_text(encoding="utf-8")
    niche = resolve_discovery_f3iche_niche(
        discovery_f3iche="manufacturing",
        industry="industrial adhesives",
        chat_transcript=transcript,
    )
    assert niche != "manufacturing_fabrication_jobshop"


def test_apex_resins_validator_fixes_classifier_gap():
    """Simulates old classifier output (batch_expiration seeds, no Customer/Supplier)."""
    transcript = (_FIXTURES / "apex_resins_recall.txt").read_text(encoding="utf-8")
    offline = finalize_offline_mvp_plan(
        transcript=transcript,
        coverage={
            "legacy_system": {"value": "Tally", "status": "confirmed"},
            "pain_point": {"value": "batch traceability and expiry tracking", "status": "confirmed"},
            "industry": {"value": "industrial adhesives", "status": "confirmed"},
        },
        mvp_focus={"archetype_id": "batch_expiration_obsolescence"},
    )
    day1 = offline["day1_doctypes"]
    assert "Customer" in day1
    assert any(d in day1 for d in ("Supplier", "Purchase Receipt"))
    assert "Sales Invoice" not in day1
    assert offline["validation"]["valid"]
