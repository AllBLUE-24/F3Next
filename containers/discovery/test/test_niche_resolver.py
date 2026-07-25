"""Tests for discovery niche resolution (Phase 2/3)."""

from __future__ import annotations

import asyncio

import pytest

from containers.discovery.niche_resolver import (
    infer_broad_f3iche,
    resolve_discovery_f3iche_niche,
    resolve_discovery_f3iche_niche_async,
)


def test_infer_broad_f3iche_from_hint():
    assert infer_broad_f3iche(f3iche_hint="manufacturing") == "manufacturing"
    assert infer_broad_f3iche(f3iche_hint="trading") == "trading"


def test_infer_broad_f3iche_from_industry():
    assert infer_broad_f3iche(industry="Industrial manufacturing plant") == "manufacturing"
    assert infer_broad_f3iche(industry="Professional consulting services") == "service"


def test_keyword_resolve_epoxy_to_chemical():
    niche = resolve_discovery_f3iche_niche(
        discovery_f3iche="manufacturing",
        industry="industrial epoxy floor coatings",
        chat_transcript="We batch produce epoxy primers for site installation.",
    )
    assert niche == "manufacturing_project_chemical"


def test_apex_resins_adhesives_not_jobshop():
    transcript = (
        "We are Apex Resins. We manufacture industrial adhesives and sealants. "
        "Chemical drums with 6-month shelf lives. Batch traceability in Excel."
    )
    niche = resolve_discovery_f3iche_niche(
        discovery_f3iche="manufacturing",
        industry="industrial adhesives",
        chat_transcript=transcript,
    )
    assert niche in ("manufacturing_project_chemical", "manufacturing_food_batch")
    assert niche != "manufacturing_fabrication_jobshop"


def test_async_resolve_keyword_source():
    niche_id, source = asyncio.run(
        resolve_discovery_f3iche_niche_async(
            discovery_f3iche="manufacturing",
            industry="epoxy coatings",
            chat_transcript="factory WIP black box",
            use_llm_niche=False,
        )
    )
    assert source == "keyword"
    assert niche_id == "manufacturing_project_chemical"


def test_async_resolve_llm_source(monkeypatch):
    async def fake_llm(**kwargs):
        return "trading_fmcg_distributor"

    monkeypatch.setattr(
        "containers.discovery.niche_resolver.resolve_discovery_f3iche_niche_with_llm",
        fake_llm,
    )

    niche_id, source = asyncio.run(
        resolve_discovery_f3iche_niche_async(
            discovery_f3iche="trading",
            industry="custom epoxy countertops sold via Instagram",
            chat_transcript="We track quotes and custom orders, not factory WIP.",
            use_llm_niche=True,
        )
    )
    assert source == "llm"
    assert niche_id == "trading_fmcg_distributor"


@pytest.mark.parametrize(
    "discovery_f3iche,industry,chat",
    [
        ("", "", ""),
        ("retail", "random stuff", "nothing matches here at all"),
        ("gibberish", "unknown vertical", "no keywords whatsoever"),
    ],
)
def test_resolve_niche_never_raises_on_unexpected_broad_category(
    discovery_f3iche: str,
    industry: str,
    chat: str,
):
    niche = resolve_discovery_f3iche_niche(
        discovery_f3iche=discovery_f3iche,
        industry=industry,
        chat_transcript=chat,
    )
    assert isinstance(niche, str)
    assert niche.strip()
