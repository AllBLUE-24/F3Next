"""
Golden MVP boundary tests (Phase 5 gate).

Deterministic scoping using Research archetypes — no live LLM required.
Run: pytest containers/discovery/test/test_mvp_boundary_golden.py -m golden
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from containers.discovery.mvp_scoping import scope_mvp_seeds
from containers.discovery.niche_resolver import f3iche_template_path
from containers.discovery.target.f3iche_seeds import load_f3iche_template_seeds

_FIXTURES = Path(__file__).parent / "fixtures"
_MATRIX_PATH = _FIXTURES / "golden_mvp_boundary.json"


def _load_matrix() -> list[dict]:
    data = json.loads(_MATRIX_PATH.read_text(encoding="utf-8"))
    return list(data.get("cases") or [])


def _active_cases() -> list[dict]:
    return [c for c in _load_matrix() if c.get("status") != "pending_research"]


def _case_id(case: dict) -> str:
    return str(case.get("id") or case.get("name"))


@pytest.mark.golden
@pytest.mark.parametrize("case", _active_cases(), ids=_case_id)
def test_golden_mvp_boundary_scoping(case: dict):
    fixture_name = case["fixture"]
    transcript = (_FIXTURES / fixture_name).read_text(encoding="utf-8").strip()
    f3iche_id = case["f3iche_id"]

    seeds, f3iche_data = load_f3iche_template_seeds(str(f3iche_template_path(f3iche_id)))
    assert seeds, f"empty template seeds for {f3iche_id}"

    result = scope_mvp_seeds(
        template_seeds=seeds,
        f3iche_id=f3iche_id,
        f3iche_data=f3iche_data,
        mvp_focus=case.get("mvp_focus") or {},
        coverage=case.get("coverage") or {},
        chat_transcript=transcript,
    )

    expect = case.get("expect") or {}
    mvp = result["mvp_seeds"]

    prefix = expect.get("scoping_mode_prefix")
    if prefix:
        assert result["scoping_mode"].startswith(prefix), result["scoping_mode"]

    if expect.get("archetype_id"):
        assert result["archetype_id"] == expect["archetype_id"]

    if expect.get("archetype_source"):
        assert result["archetype_source"] == expect["archetype_source"]

    for dt in expect.get("must_include") or []:
        assert dt in mvp, f"expected {dt} in mvp_seeds, got {mvp}"

    for dt in expect.get("must_exclude") or []:
        assert dt not in mvp, f"expected {dt} deferred, got {mvp}"


@pytest.mark.golden
def test_golden_matrix_pending_cases_documented():
    pending = [c for c in _load_matrix() if c.get("status") == "pending_research"]
    assert pending, "expected at least one pending_research row for Research handoff"
    for case in pending:
        assert case.get("notes"), f"{case.get('id')} pending row needs notes"


@pytest.mark.golden
def test_defer_modules_in_golden_custom_order_case_when_archetype_exists():
    """When custom_order_pipeline archetype lands, enable GM-DISC-04 in matrix."""
    case = next(c for c in _load_matrix() if c.get("id") == "GM-DISC-04")
    if case.get("status") == "pending_research":
        pytest.skip("GM-DISC-04 pending Research archetype custom_order_pipeline")

    transcript = (_FIXTURES / case["fixture"]).read_text(encoding="utf-8").strip()
    seeds, f3iche_data = load_f3iche_template_seeds(
        str(f3iche_template_path(case["f3iche_id"]))
    )
    result = scope_mvp_seeds(
        template_seeds=seeds,
        f3iche_id=case["f3iche_id"],
        f3iche_data=f3iche_data,
        mvp_focus=case.get("mvp_focus") or {},
        coverage=case.get("coverage") or {},
        chat_transcript=transcript,
    )
    for dt in case["expect"]["must_include"]:
        assert dt in result["mvp_seeds"]
