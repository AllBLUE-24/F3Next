"""Tests for new trading/service F3iche templates."""

from __future__ import annotations

import asyncio

from containers.discovery.niche_resolver import f3iche_template_exists, f3iche_template_path
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
