"""Tests for Step 8 MVP boundary and corpus-aware seed selection."""
from __future__ import annotations

from containers.implementation.target_agent.mvp_boundary import (
    canonicalize_template_doctype,
    defer_without_evidence,
    merge_seed_sources,
    reconcile_setup_step_actions,
    refine_mvp_seeds,
    seeds_from_corpus,
)


def test_canonicalize_template_doctype():
    assert canonicalize_template_doctype("BOM (Formulation)") == "BOM"
    assert canonicalize_template_doctype("Stock Entry (Issue, Transfer, Manufacture)") == "Stock Entry"


def test_seeds_from_corpus_likely_doctypes():
    corpus = {
        "corpus_summary": "Purchase orders and client project orders",
        "files": [
            {
                "filename": "raw_purchase_orders.csv",
                "business_description": "Supplier purchase orders",
                "likely_erpnext_doctypes": ["Purchase Order", "Supplier"],
            },
            {
                "filename": "client_orders.csv",
                "business_description": "Client installation projects",
                "likely_erpnext_doctypes": ["Project", "Sales Order", "Customer"],
            },
        ],
    }
    seeds, evidence = seeds_from_corpus(corpus)
    assert "Purchase Order" in seeds
    assert "Project" in seeds
    assert len(evidence) == 2


def test_seeds_from_filename_hints():
    corpus = {
        "corpus_summary": "Small upload",
        "files": [{"filename": "raw_purchase_orders.csv", "business_description": "PO data"}],
    }
    seeds, _ = seeds_from_corpus(corpus)
    assert "Purchase Order" in seeds


def test_defer_manufacturing_without_evidence():
    seeds = ["Project", "Sales Order", "Item", "Work Order", "BOM"]
    corpus_seeds = ["Project", "Sales Order", "Item"]
    active, deferred = defer_without_evidence(seeds, corpus_seeds, [])
    assert "Work Order" in deferred
    assert "BOM" in deferred
    assert "Project" in active


def test_merge_seed_sources_preserves_order():
    merged = merge_seed_sources(["Item"], ["Purchase Order", "Item"], ["Customer"])
    assert merged == ["Item", "Purchase Order", "Customer"]


def test_refine_mvp_seeds_injects_party_masters():
    seeds = ["Project", "Item", "Sales Order", "Purchase Order", "Stock Entry"]
    evidence = [
        {
            "file": "messy_partners.csv",
            "suggested_seeds": ["Customer", "Supplier"],
        }
    ]
    active, deferred = refine_mvp_seeds(seeds, [], evidence, [])
    assert "Customer" in active
    assert "Supplier" in active


def test_refine_mvp_seeds_defers_optional_without_evidence():
    seeds = [
        "Project", "Item", "Stock Entry", "Purchase Order", "Sales Order",
        "Item Variant", "Quotation", "Delivery Note", "Task", "Timesheet",
    ]
    active, deferred = refine_mvp_seeds(seeds, ["Project", "Item"], [], [])
    assert "Item Variant" in deferred
    assert "Quotation" in deferred
    assert "Delivery Note" in deferred
    assert "Task" in deferred
    assert "Timesheet" in deferred
    assert "Stock Entry" in active


def test_reconcile_work_order_requires_bom():
    steps = [
        {"doctype": "BOM", "action": "optional_if_absent"},
        {"doctype": "Work Order", "action": "must_create"},
    ]
    out = reconcile_setup_step_actions(steps, ["Work Order", "BOM"])
    bom = next(s for s in out if s["doctype"] == "BOM")
    assert bom["action"] == "must_create"
