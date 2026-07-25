"""
Live routing matrix tests (Phase 5).

Deterministic rows: niche resolution + signal shadow rankings (no LLM).
Live rows: full discovery pipeline — run only with DISCOVERY_LIVE_MATRIX=1.

  pytest containers/discovery/test/test_live_routing_matrix.py -m routing_matrix
  DISCOVERY_LIVE_MATRIX=1 pytest containers/discovery/test/test_live_routing_matrix.py -m live_llm
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

import pytest

from containers.discovery.archetype_registry import signal_match_rankings
from containers.discovery.niche_resolver import resolve_discovery_f3iche_niche

_FIXTURES = Path(__file__).parent / "fixtures"
_MATRIX_PATH = _FIXTURES / "live_routing_matrix.json"


def _load_matrix() -> dict:
    return json.loads(_MATRIX_PATH.read_text(encoding="utf-8"))


def _load_cases(*, live: bool) -> list[dict]:
    cases = list(_load_matrix().get("cases") or [])
    if live:
        return [c for c in cases if not c.get("deterministic_only")]
    return cases


def _case_id(case: dict) -> str:
    return str(case.get("id") or case.get("name"))


def _transcript(case: dict) -> str:
    return (_FIXTURES / case["fixture"]).read_text(encoding="utf-8").strip()


def _accepted_archetypes(case: dict) -> set[str]:
    ids = {str(case["expect_archetype"]).strip()}
    for alt in case.get("accept_alternate_archetypes") or []:
        ids.add(str(alt).strip())
    return ids


def _archetype_matches(case: dict, llm_id: str, scoped_id: str) -> bool:
    accepted = _accepted_archetypes(case)
    if scoped_id in accepted:
        return True
    if llm_id in accepted:
        return True
    return False


def _broad_f3iche(case: dict) -> str:
    if case.get("broad_f3iche"):
        return str(case["broad_f3iche"])
    niche = str(case.get("expect_niche") or "")
    if niche.startswith("service_"):
        return "service"
    if niche.startswith("trading_"):
        return "trading"
    return "manufacturing"


@pytest.mark.routing_matrix
@pytest.mark.parametrize("case", _load_cases(live=False), ids=_case_id)
def test_live_matrix_niche_resolution(case: dict):
    text = _transcript(case)
    niche = resolve_discovery_f3iche_niche(
        discovery_f3iche=_broad_f3iche(case),
        industry="",
        chat_transcript=text,
    )
    assert niche == case["expect_niche"], f"got {niche!r}, expected {case['expect_niche']!r}"


@pytest.mark.routing_matrix
@pytest.mark.parametrize(
    "case",
    [c for c in _load_cases(live=False) if (c.get("deterministic") or {}).get("signal_top")],
    ids=_case_id,
)
def test_live_matrix_signal_top(case: dict):
    text = _transcript(case)
    f3iche_id = case["f3iche_id"]
    expected = case["deterministic"]["signal_top"]
    ranked = signal_match_rankings(text, f3iche_id, top_k=5)
    assert ranked, f"no signal hits for {case['id']}"
    assert ranked[0]["archetype_id"] == expected, ranked


def _live_matrix_enabled() -> bool:
    return os.getenv("DISCOVERY_LIVE_MATRIX", "").lower() in ("1", "true", "yes")


@pytest.mark.live_llm
@pytest.mark.parametrize("case", _load_cases(live=True), ids=_case_id)
def test_live_matrix_llm_archetype_routing(case: dict):
    if not _live_matrix_enabled():
        pytest.skip("Set DISCOVERY_LIVE_MATRIX=1 to run live LLM routing matrix")

    from containers.discovery.test.harness_mvp_boundary import (
        _check_expect_archetype,
        _messages_from_user_text,
        _run_with_llm,
    )

    text = _transcript(case)
    messages = _messages_from_user_text(text)
    result = asyncio.run(_run_with_llm(messages, enhance_target=False, use_llm_niche=None))

    mvp = result.get("mvp_boundary") or {}
    scoping = result.get("scoping") or {}
    focus = result.get("mvp_focus") or mvp.get("mvp_focus") or {}
    llm_id = str(focus.get("archetype_id") or "").strip()
    scoped_id = str(mvp.get("archetype_id") or scoping.get("archetype_id") or "").strip()
    if llm_id.lower() in ("null", "none"):
        llm_id = ""

    assert _archetype_matches(case, llm_id, scoped_id), (
        f"{case['id']}: expected one of {_accepted_archetypes(case)!r}; "
        f"LLM={llm_id!r}, scoped={scoped_id!r}"
    )


@pytest.mark.routing_matrix
def test_live_matrix_gate_threshold_documented():
    meta = _load_matrix().get("_meta") or {}
    gate = meta.get("gate_min_accuracy")
    assert gate is not None
    assert 0.5 <= float(gate) <= 1.0
