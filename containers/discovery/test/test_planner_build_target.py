"""Tests for planner-validated scoping in build_discovery_target."""

from __future__ import annotations

import asyncio

from containers.discovery.target.build_target import build_discovery_target

CHEMICAL_TEMPLATE = [
    "Item", "Batch", "BOM", "Work Order", "Delivery Note", "Stock Entry",
    "Customer", "Supplier", "Warehouse", "Purchase Receipt",
    "Sales Invoice", "Payment Entry",
]


def test_planner_seeds_override_archetype_hints():
    planner_seeds = [
        "Batch", "Item", "Stock Entry", "Delivery Note", "Warehouse",
        "Customer", "Supplier", "Purchase Receipt",
    ]
    result = asyncio.run(
        build_discovery_target(
            f3iche="manufacturing_project_chemical",
            mvp_focus={
                "primary_bottleneck": "batch traceability and recall",
                "archetype_id": "batch_expiration_obsolescence",
                "planner_day1_seeds": planner_seeds,
                "defer_modules_mentioned": ["Sales Invoice", "Payment Entry"],
                "plan_reasoning": "Trace upstream raw batches and downstream customer dispatch.",
            },
            chat_transcript="Apex Resins adhesives batch recall Tally",
        )
    )
    assert result["mvp_boundary"]["mode"] == "planner_validated"
    assert "Customer" in result["seed_doctypes"]
    assert "Purchase Receipt" in result["seed_doctypes"]
    assert "Sales Invoice" in result["deferred_doctypes"]
    assert result["mvp_boundary"]["planner_validated"] is True
