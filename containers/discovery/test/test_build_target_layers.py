"""Tests for graph-correct setup layer ordering in build_discovery_target."""

from __future__ import annotations

import asyncio

from containers.discovery.target.build_target import build_discovery_target

CHEMICAL_PLANNER_SEEDS = [
    "Batch",
    "Item",
    "Stock Entry",
    "Delivery Note",
    "Warehouse",
    "Customer",
    "Supplier",
    "Purchase Receipt",
    "BOM",
    "Work Order",
]


def _step_index(setup_steps: list[dict], doctype: str) -> int:
    for step in setup_steps:
        if step["doctype"] == doctype:
            return step["step"]
    raise AssertionError(f"{doctype} not in setup_steps")


def test_setup_steps_order_masters_before_transactions():
    result = asyncio.run(
        build_discovery_target(
            f3iche="manufacturing_project_chemical",
            mvp_focus={
                "primary_bottleneck": "batch traceability and recall",
                "planner_day1_seeds": CHEMICAL_PLANNER_SEEDS,
                "plan_reasoning": "Trace upstream raw batches and downstream customer dispatch.",
            },
            chat_transcript="Apex Resins adhesives batch recall Tally",
        )
    )
    steps = result["setup_steps"]
    assert steps, "expected non-empty setup_steps"

    item_step = _step_index(steps, "Item")
    work_order_step = _step_index(steps, "Work Order")
    delivery_step = _step_index(steps, "Delivery Note")

    assert item_step < work_order_step, "Item (master) must precede Work Order (transaction)"
    assert item_step < delivery_step, "Item (master) must precede Delivery Note (fulfillment)"

    phases = [s["phase"] for s in steps if s["doctype"] == "Item"]
    assert phases == ["phase_b_master"]


def test_import_phases_split_config_master_transactional():
    result = asyncio.run(
        build_discovery_target(
            f3iche="manufacturing_project_chemical",
            mvp_focus={
                "planner_day1_seeds": CHEMICAL_PLANNER_SEEDS,
            },
            chat_transcript="chemical manufacturing batch traceability",
        )
    )
    phases = result["import_phases"]
    config = phases["phase_a_config"]["doctypes"]
    master = phases["phase_b_master"]["doctypes"]
    transactional = phases["phase_c_transactional"]["doctypes"]

    assert "Company" in config or "Warehouse" in config
    assert "Item" in master
    assert "Work Order" in transactional or "Stock Entry" in transactional


def test_org_skeleton_from_chemical_f3iche():
    result = asyncio.run(
        build_discovery_target(
            f3iche="manufacturing_project_chemical",
            mvp_focus={"planner_day1_seeds": CHEMICAL_PLANNER_SEEDS},
            chat_transcript="Apex Resins chemical batch",
        )
    )
    skeleton = result["mvp_boundary"].get("org_skeleton") or {}
    warehouses = skeleton.get("required_warehouses") or []
    assert any("RM" in w for w in warehouses)
    assert skeleton.get("valuation_method") == "FIFO"
