"""Tests for Discovery MVP plan validator (Phase 1)."""

from __future__ import annotations

from pathlib import Path

import pytest

from containers.discovery.mvp_validator import validate_mvp_plan

FIXTURES = Path(__file__).parent / "fixtures"

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
    "Customer",
    "Supplier",
    "Warehouse",
    "Purchase Receipt",
    "Purchase Order",
    "Sales Invoice",
    "Payment Entry",
]

APEX_TRANSCRIPT = (FIXTURES / "apex_resins_recall.txt").read_text(encoding="utf-8")


def test_promotes_customer_when_delivery_note_seeded():
    result = validate_mvp_plan(
        day1_entries=["Batch", "Item", "Stock Entry", "Delivery Note", "Warehouse"],
        deferred_entries=["Sales Invoice", "Payment Entry"],
        niche_id="manufacturing_project_chemical",
        chat_transcript=APEX_TRANSCRIPT,
        template_seeds=CHEMICAL_TEMPLATE,
        legacy_system="Tally",
    )
    assert "Customer" in result.day1_doctypes
    assert "Customer" in result.promoted_doctypes
    assert result.valid


def test_apex_recall_promotes_upstream_trace():
    """Raw material + customer recall signals require Supplier/Purchase Receipt path."""
    result = validate_mvp_plan(
        day1_entries=["Batch", "Item", "Stock Entry", "Delivery Note", "Warehouse"],
        deferred_entries=["Sales Invoice", "Payment Entry", "Customer"],
        niche_id="manufacturing_project_chemical",
        chat_transcript=APEX_TRANSCRIPT,
        template_seeds=CHEMICAL_TEMPLATE,
        legacy_system="Tally",
    )
    assert "Customer" in result.day1_doctypes
    assert any(d in result.day1_doctypes for d in ("Supplier", "Purchase Receipt"))
    assert result.valid


def test_jobshop_niche_warns_on_batch_expiry():
    result = validate_mvp_plan(
        day1_entries=["Batch", "Item", "Delivery Note"],
        deferred_entries=[],
        niche_id="manufacturing_fabrication_jobshop",
        chat_transcript=APEX_TRANSCRIPT,
        template_seeds=CHEMICAL_TEMPLATE,
    )
    codes = {i.code for i in result.issues}
    assert "NICHE_MISMATCH" in codes


def test_dual_system_defers_invoicing_not_customer_trace():
    result = validate_mvp_plan(
        day1_entries=[
            "Batch", "Item", "Customer", "Delivery Note",
            "Sales Invoice", "Payment Entry",
        ],
        deferred_entries=[],
        niche_id="manufacturing_project_chemical",
        chat_transcript=APEX_TRANSCRIPT,
        template_seeds=CHEMICAL_TEMPLATE,
        legacy_system="Tally Prime",
    )
    assert "Sales Invoice" not in result.day1_doctypes
    assert "Payment Entry" not in result.day1_doctypes
    assert "Customer" in result.day1_doctypes


def test_unknown_doctype_is_error():
    result = validate_mvp_plan(
        day1_entries=["NotARealDoctype"],
        deferred_entries=[],
        niche_id="manufacturing_project_chemical",
        chat_transcript="simple manufacturing",
        template_seeds=CHEMICAL_TEMPLATE,
    )
    assert not result.valid
    assert any(i.code == "UNKNOWN_DOCTYPE" for i in result.issues)


@pytest.mark.golden
def test_gm_disc_05_apex_resins_recall_plan():
    """GM-DISC-05: validated planner scope for chemical recall + Tally."""
    result = validate_mvp_plan(
        day1_entries=[
            "Batch", "Item", "Stock Entry", "Delivery Note", "Warehouse",
            "Customer", "Supplier", "Purchase Receipt",
        ],
        deferred_entries=["Sales Invoice", "Payment Entry", "BOM", "Work Order"],
        niche_id="manufacturing_project_chemical",
        chat_transcript=APEX_TRANSCRIPT,
        template_seeds=CHEMICAL_TEMPLATE,
        legacy_system="Tally",
    )
    assert result.valid
    for dt in ("Batch", "Customer", "Delivery Note"):
        assert dt in result.day1_doctypes
    assert any(d in result.day1_doctypes for d in ("Supplier", "Purchase Receipt"))
    assert "Sales Invoice" not in result.day1_doctypes
