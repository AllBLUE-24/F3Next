"""Tests for clarification → validator policy (MTS/MTO, trace, routing, QC)."""

from __future__ import annotations

from pathlib import Path

from containers.discovery.discovery_clarification_policy import (
    apply_clarification_policy,
    clarification_context_for_explainer,
)
from containers.discovery.mvp_validator import validate_mvp_plan

FIXTURES = Path(__file__).parent / "fixtures"
YIELD_TRANSCRIPT = (FIXTURES / "cleaning_chemicals_yield.txt").read_text(encoding="utf-8")

CHEMICAL_TEMPLATE = [
    "Item",
    "Batch",
    "BOM",
    "Work Order",
    "Job Card",
    "Stock Entry",
    "Warehouse",
    "Quotation",
    "Sales Order",
    "Delivery Note",
    "Customer",
    "Supplier",
    "Purchase Receipt",
    "Quality Inspection",
    "Quality Inspection Template",
    "Workstation",
]


def _apply_policy(
    day1: list[str],
    deferred: list[str],
    answers: dict,
    *,
    template: list[str] | None = None,
) -> tuple[list[str], list[str]]:
    template_set = set(template or CHEMICAL_TEMPLATE)
    deferred_set = set(deferred)
    promoted: list[str] = []
    notes: list[str] = []
    apply_clarification_policy(
        day1=day1,
        deferred=deferred,
        deferred_set=deferred_set,
        promoted=promoted,
        template_set=template_set,
        notes=notes,
        clarification_answers=answers,
    )
    return day1, deferred


def test_mts_defers_sales_order_and_quotation():
    day1 = ["Item", "BOM", "Work Order", "Stock Entry", "Sales Order", "Quotation"]
    deferred: list[str] = []
    day1, deferred = _apply_policy(
        day1,
        deferred,
        {"manufacturing_strategy": "mts"},
    )
    assert "Sales Order" not in day1
    assert "Quotation" not in day1
    assert "Sales Order" in deferred


def test_mto_promotes_sales_order_when_manufacturing():
    day1 = ["Item", "BOM", "Work Order", "Stock Entry"]
    deferred = ["Sales Order"]
    day1, deferred = _apply_policy(
        day1,
        deferred,
        {"manufacturing_strategy": "mto"},
    )
    assert "Sales Order" in day1
    assert "Sales Order" not in deferred


def test_routing_no_defers_job_card_and_workstation():
    day1 = ["Item", "BOM", "Work Order", "Job Card", "Workstation", "Stock Entry"]
    deferred: list[str] = []
    day1, deferred = _apply_policy(
        day1,
        deferred,
        {"routing_depth": "no"},
    )
    assert "Job Card" not in day1
    assert "Workstation" not in day1


def test_expiry_trace_promotes_batch():
    day1 = ["Item", "BOM", "Work Order", "Stock Entry"]
    deferred = ["Batch"]
    day1, deferred = _apply_policy(
        day1,
        deferred,
        {"trace_direction": ["expiry"]},
    )
    assert "Batch" in day1


def test_clarification_context_for_explainer_includes_mts():
    ctx = clarification_context_for_explainer({"manufacturing_strategy": "mts"})
    assert "Make-to-stock" in ctx
    assert "MUST align" in ctx


def test_yield_mts_costing_only_integration():
    """Test #2 v1.5: MTS + total batch yield + costing-only → no SO/QI, Batch stays."""
    result = validate_mvp_plan(
        day1_entries=[
            "Item", "BOM", "Work Order", "Batch", "Job Card", "Stock Entry",
            "Warehouse", "Sales Order", "Purchase Receipt", "Supplier",
            "Quality Inspection",
        ],
        deferred_entries=["Quotation", "Delivery Note", "Customer"],
        niche_id="manufacturing_project_chemical",
        chat_transcript=YIELD_TRANSCRIPT,
        template_seeds=CHEMICAL_TEMPLATE,
        legacy_system="Tally",
        clarification_answers={
            "manufacturing_strategy": "mts",
            "routing_depth": "no",
            "quality_gates": "costing_only",
        },
    )
    assert result.valid
    assert "Batch" in result.day1_doctypes
    assert "Sales Order" not in result.day1_doctypes
    assert "Job Card" not in result.day1_doctypes
    assert "Quality Inspection" not in result.day1_doctypes
