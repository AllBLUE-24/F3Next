"""Tests for Phase 1 archetype routing observability (shadow signal rankings)."""

from __future__ import annotations

from containers.discovery.archetype_registry import build_routing_diagnostics, signal_match_rankings
from containers.discovery.mvp_scoping import scope_mvp_seeds

CHEMICAL_F3ICHE = "manufacturing_project_chemical"

CHEMICAL_TEMPLATE = [
    "Item",
    "Batch",
    "BOM",
    "Work Order",
    "Quotation",
    "Sales Order",
    "Project",
    "Stock Entry",
    "Quality Inspection",
]

WIP_TRANSCRIPT = (
    "excel sheets flying around work in progress black box true production cost "
    "batch-wise profitability chemical formulations"
)


def test_signal_match_rankings_returns_top_candidates():
    ranked = signal_match_rankings(WIP_TRANSCRIPT, CHEMICAL_F3ICHE, top_k=3)
    assert len(ranked) >= 1
    assert ranked[0]["score"] >= ranked[-1]["score"]
    assert "archetype_id" in ranked[0]


ISO_TRANSCRIPT = (
    "ISO audit requires strict quality gates on all incoming stock and raw material batch "
    "certificate of analysis incoming inspection"
)


def test_routing_diagnostics_flags_llm_mismatch():
    diag = build_routing_diagnostics(
        context_text=ISO_TRANSCRIPT,
        f3iche_id=CHEMICAL_F3ICHE,
        llm_archetype_id="custom_order_pipeline",
        chosen_archetype_id="custom_order_pipeline",
        archetype_source="mvp_focus",
    )
    assert diag["signal_match_candidates"]
    assert diag["llm_archetype_signal_score"] == 0
    top = diag["signal_match_candidates"][0]["archetype_id"]
    assert top == "incoming_quality_compliance"
    assert diag["archetype_routing_mismatch"] is True
    assert diag["archetype_routing_note"]


def test_scope_mvp_seeds_includes_routing_diagnostics_on_mvp_focus():
    result = scope_mvp_seeds(
        template_seeds=CHEMICAL_TEMPLATE,
        f3iche_id=CHEMICAL_F3ICHE,
        mvp_focus={
            "archetype_id": "custom_order_pipeline",
            "primary_bottleneck": "custom orders",
        },
        chat_transcript=WIP_TRANSCRIPT,
    )
    assert "signal_match_candidates" in result
    assert isinstance(result["signal_match_candidates"], list)
    assert result["archetype_source"] == "mvp_focus"
    assert result["signal_match_score"] is None
    assert result["llm_archetype_id"] == "custom_order_pipeline"
    assert "llm_archetype_signal_score" in result


def test_scope_mvp_seeds_coerces_string_null_llm_id_in_diagnostics():
    result = scope_mvp_seeds(
        template_seeds=CHEMICAL_TEMPLATE,
        f3iche_id=CHEMICAL_F3ICHE,
        mvp_focus={"archetype_id": "null", "primary_bottleneck": "project billing"},
        chat_transcript="tracking project milestones and milestone billing on sales order",
    )
    assert result["llm_archetype_id"] is None
    assert result["invalid_archetype_id"] == "null"
