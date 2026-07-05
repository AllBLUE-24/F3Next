"""Tests for bottleneck-driven Discovery MVP scoping (legacy path — see discovery/test)."""

from __future__ import annotations

from containers.discovery.mvp_scoping import scope_mvp_seeds

CHEMICAL_F3ICHE = "manufacturing_project_chemical"

GREEN_SURFACE_TRANSCRIPT = (
    "We are Green Surface, a manufacturer of industrial epoxy coatings. "
    "Accounting is perfectly managed in Tally Prime. "
    "Tally treats our factory like a black box. "
    "Zero visibility into Work-In-Progress (WIP), machine overhead, or batch-wise profitability. "
    "Chemical formulations and production schedules in disconnected Excel sheets."
)

CHEMICAL_TEMPLATE = [
    "Item",
    "Item Variant",
    "Batch",
    "BOM",
    "Work Order",
    "Job Card",
    "Project",
    "Task",
    "Timesheet",
    "Quotation",
    "Sales Order",
    "Delivery Note",
    "Stock Entry",
    "Quality Inspection",
    "Quality Inspection Template",
]


def test_green_surface_wip_scopes_via_archetype_id():
    result = scope_mvp_seeds(
        template_seeds=CHEMICAL_TEMPLATE,
        f3iche_id=CHEMICAL_F3ICHE,
        mvp_focus={
            "primary_bottleneck": "Zero visibility into WIP and batch-wise profitability",
            "archetype_id": "factory_wip_bridge",
            "functional_requirements": [
                "Real-time WIP tracking",
                "Bridge sales to factory fulfillment",
            ],
        },
        coverage={
            "legacy_system": {"value": "Tally Prime", "status": "confirmed"},
            "pain_point": {"value": "Disconnected Excel BOMs", "status": "confirmed"},
        },
        chat_transcript=GREEN_SURFACE_TRANSCRIPT,
    )

    mvp = result["mvp_seeds"]
    assert result["scoping_mode"].startswith("archetype_factory_wip_bridge")
    assert len(mvp) <= 8
    assert "Item" in mvp
    assert "BOM" in mvp
    assert "Work Order" in mvp
    assert "Quality Inspection" in mvp
    assert "Timesheet" not in mvp
    assert result["dual_system_note"]


def test_user_override_wins():
    result = scope_mvp_seeds(
        template_seeds=CHEMICAL_TEMPLATE,
        f3iche_id=CHEMICAL_F3ICHE,
        user_confirmed_override=["Item", "BOM"],
    )
    assert result["mvp_seeds"] == ["Item", "BOM"]
    assert result["scoping_mode"] == "user_confirmed"
