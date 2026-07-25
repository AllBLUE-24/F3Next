"""Tests for new trading/service F3iche templates."""

from __future__ import annotations

import asyncio

from containers.discovery.discovery_clarify import build_clarifying_questions
from containers.discovery.mvp_plan_draft import finalize_offline_mvp_plan
from containers.discovery.niche_resolver import f3iche_template_exists, f3iche_template_path, resolve_discovery_f3iche_niche
from containers.discovery.target.build_target import build_discovery_target
from containers.discovery.target.f3iche_seeds import (
    load_f3iche_playbook,
    load_f3iche_template_seeds,
    org_skeleton_from_f3iche,
)


def test_trading_fmcg_template_loads_seeds_and_questions():
    assert f3iche_template_exists("trading_fmcg_distributor")
    playbook = load_f3iche_playbook("trading_fmcg_distributor")
    assert playbook.get("questions")
    seeds, data = load_f3iche_template_seeds(str(f3iche_template_path("trading_fmcg_distributor")))
    assert "Item" in seeds
    assert "Batch" in seeds
    skeleton = org_skeleton_from_f3iche(data)
    assert skeleton.get("required_warehouses")


def test_service_professional_template_loads():
    assert f3iche_template_exists("service_professional")
    playbook = load_f3iche_playbook("service_professional")
    assert any("technician" in q["question"].lower() for q in playbook["questions"])


def test_build_target_for_trading_niche():
    result = asyncio.run(
        build_discovery_target(
            f3iche="trading_fmcg_distributor",
            mvp_focus={
                "planner_day1_seeds": [
                    "Item", "Batch", "Warehouse", "Customer", "Delivery Note", "Stock Entry",
                ],
            },
            chat_transcript="FMCG distributor expiry tracking Tally",
        )
    )
    assert result["mvp_boundary"]["template_status"]["template_available"] is True
    assert result["mvp_boundary"].get("org_skeleton")


def _offline_chain(transcript: str, *, broad: str, industry: str) -> dict:
    niche_id = resolve_discovery_f3iche_niche(
        discovery_f3iche=broad,
        industry=industry,
        chat_transcript=transcript,
    )
    questions = build_clarifying_questions(transcript, niche_id=niche_id)
    offline = finalize_offline_mvp_plan(
        transcript=transcript,
        coverage={
            "industry": {"value": industry},
            "pain_point": {"value": "stock visibility"},
            "legacy_system": {"value": "Tally"},
        },
        industry=industry,
        f3iche_hint=broad,
    )
    target = asyncio.run(
        build_discovery_target(
            f3iche=offline["f3iche_niche"],
            mvp_focus=offline["mvp_focus"],
            chat_transcript=transcript,
            niche_resolution_source=offline["niche_resolution_source"],
        )
    )
    return {
        "niche_id": niche_id,
        "questions": questions,
        "offline": offline,
        "target": target,
    }


def test_trading_offline_discovery_chain_smoke():
    transcript = (
        "We are an FMCG distributor with 40 SKUs and near-expiry write-offs. "
        "Beat routes and van delivery; accounting stays in Tally."
    )
    result = _offline_chain(
        transcript,
        broad="trading",
        industry="FMCG wholesale distributor",
    )
    assert result["niche_id"] == "trading_fmcg_distributor"
    assert result["offline"]["f3iche_niche"] == "trading_fmcg_distributor"
    assert result["offline"]["day1_doctypes"]
    assert result["target"]["mvp_boundary"]["template_status"]["template_available"] is True
    assert result["questions"]


def test_service_offline_discovery_chain_smoke():
    transcript = (
        "We run a field service team for HVAC maintenance. Technicians get WhatsApp "
        "repair requests with no central dispatch queue. Spare parts van stock is chaos."
    )
    result = _offline_chain(
        transcript,
        broad="service",
        industry="HVAC field service",
    )
    assert result["niche_id"] == "service_professional"
    assert result["offline"]["f3iche_niche"] == "service_professional"
    assert result["offline"]["day1_doctypes"]
    assert result["target"]["mvp_boundary"]["template_status"]["template_available"] is True
