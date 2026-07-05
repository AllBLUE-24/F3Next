"""Tests for archetype-driven Discovery MVP scoping (Phase 1)."""

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


def test_archetype_id_drives_factory_wip_seeds():
    result = scope_mvp_seeds(
        template_seeds=CHEMICAL_TEMPLATE,
        f3iche_id=CHEMICAL_F3ICHE,
        mvp_focus={
            "primary_bottleneck": "Zero visibility into WIP",
            "archetype_id": "factory_wip_bridge",
            "functional_requirements": ["wip_tracking"],
        },
        coverage={
            "legacy_system": {"value": "Tally Prime", "status": "confirmed"},
            "pain_point": {"value": "WIP black box", "status": "confirmed"},
        },
        chat_transcript=GREEN_SURFACE_TRANSCRIPT,
    )

    mvp = result["mvp_seeds"]
    assert result["scoping_mode"].startswith("archetype_factory_wip_bridge")
    assert result["archetype_id"] == "factory_wip_bridge"
    assert result["archetype_source"] == "mvp_focus"
    assert "Item" in mvp
    assert "BOM" in mvp
    assert "Work Order" in mvp
    assert "Quality Inspection" in mvp
    assert "Quotation" not in mvp
    assert result["dual_system_note"]


def test_scrap_wastage_archetype_not_wip_regex():
    """ISO/quality pain with formulations in text must follow scrap archetype, not WIP regex."""
    result = scope_mvp_seeds(
        template_seeds=CHEMICAL_TEMPLATE,
        f3iche_id=CHEMICAL_F3ICHE,
        mvp_focus={
            "primary_bottleneck": "strict quality gates on incoming stock",
            "archetype_id": "scrap_wastage",
            "functional_requirements": ["quality_control"],
        },
        chat_transcript=(
            "We manufacture chemical primers. Formulations need strict inspection "
            "of every raw material batch."
        ),
    )

    mvp = result["mvp_seeds"]
    assert result["archetype_id"] == "scrap_wastage"
    assert "Stock Entry" in mvp
    assert "Batch" in mvp
    assert "Project" in mvp
    assert "Work Order" not in mvp


def test_signal_match_inventory_visibility():
    result = scope_mvp_seeds(
        template_seeds=CHEMICAL_TEMPLATE,
        f3iche_id=CHEMICAL_F3ICHE,
        chat_transcript=(
            "Part A and Part B mismatch stranded hardener hazmat 55 gallon drum batch tracking"
        ),
    )

    assert result["archetype_source"] == "signal_match"
    assert result["archetype_id"] == "inventory_visibility"
    assert "Item" in result["mvp_seeds"]
    assert "Batch" in result["mvp_seeds"]


def test_minimal_fallback_without_archetype():
    result = scope_mvp_seeds(
        template_seeds=CHEMICAL_TEMPLATE,
        f3iche_id=CHEMICAL_F3ICHE,
        chat_transcript="We sell custom furniture online with no ERP today.",
    )

    assert result["scoping_mode"] == "minimal_fallback"
    assert result["mvp_seeds"] == ["Item"]
    assert "Quotation" in result["deferred_seeds"]


def test_defer_modules_mentioned_removes_doctypes():
    result = scope_mvp_seeds(
        template_seeds=CHEMICAL_TEMPLATE,
        f3iche_id=CHEMICAL_F3ICHE,
        mvp_focus={
            "primary_bottleneck": "custom orders",
            "archetype_id": "factory_wip_bridge",
            "defer_modules_mentioned": ["Work Order", "Job Card"],
        },
        chat_transcript="We don't care about machine overhead right now.",
    )
    mvp = result["mvp_seeds"]
    assert "Work Order" not in mvp
    assert "Job Card" not in mvp
    assert "Item" in mvp
    assert "BOM" in mvp


def test_user_override_wins():
    result = scope_mvp_seeds(
        template_seeds=CHEMICAL_TEMPLATE,
        f3iche_id=CHEMICAL_F3ICHE,
        user_confirmed_override=["Item", "BOM"],
    )
    assert result["mvp_seeds"] == ["Item", "BOM"]
    assert result["scoping_mode"] == "user_confirmed"


def test_invalid_archetype_id_falls_back_to_signal_match():
    result = scope_mvp_seeds(
        template_seeds=CHEMICAL_TEMPLATE,
        f3iche_id=CHEMICAL_F3ICHE,
        mvp_focus={
            "primary_bottleneck": "inventory",
            "archetype_id": "not_a_real_archetype",
        },
        chat_transcript="Part A and Part B mismatch stranded hardener hazmat batch",
    )
    assert result["invalid_archetype_id"] == "not_a_real_archetype"
    assert result["archetype_source"] == "signal_match"
    assert result["archetype_id"] == "inventory_visibility"
