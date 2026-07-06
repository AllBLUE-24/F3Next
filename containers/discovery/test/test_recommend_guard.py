"""Tests for Phase 2 recommend guardrails."""

from __future__ import annotations

from containers.discovery.recommend_guard import apply_recommend_guard, normalize_archetype_id

CHEMICAL = "manufacturing_project_chemical"


def test_normalize_archetype_id_coerces_null_string():
    assert normalize_archetype_id("null") is None
    assert normalize_archetype_id("NONE") is None
    assert normalize_archetype_id("factory_wip_bridge") == "factory_wip_bridge"


def test_apply_recommend_guard_clears_unknown_id():
    rec = {
        "mvp_focus": {
            "archetype_id": "not_a_real_archetype",
            "functional_requirements": ["invented_req"],
        }
    }
    out = apply_recommend_guard(rec, f3iche_id=CHEMICAL)
    assert out["mvp_focus"]["archetype_id"] is None
    assert "_recommend_guard" in out


def test_apply_recommend_guard_copies_kb_functional_requirements():
    rec = {
        "mvp_focus": {
            "archetype_id": "custom_order_pipeline",
            "functional_requirements": ["invented_req"],
        }
    }
    out = apply_recommend_guard(rec, f3iche_id=CHEMICAL)
    assert out["mvp_focus"]["archetype_id"] == "custom_order_pipeline"
    assert "link_quotation_to_project" in out["mvp_focus"]["functional_requirements"]
    assert "invented_req" not in out["mvp_focus"]["functional_requirements"]
