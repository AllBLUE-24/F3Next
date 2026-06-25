"""Tests for deterministic signals_registry scoring."""
from __future__ import annotations

from containers.implementation.signals_agent.signals_scorer import (
    apply_discovery_prior,
    blend_llm_with_registry,
    score_manifest,
)

GREEN_SURFACE_FILES = {
    "raw_purchase_orders.csv": (
        "PO_Number,Vendor_Name,Item,Ordered_Qty,Price_Per_Unit\r\n"
        "PO-26-001,Gupta Chemical Traders,RM-EPOX-LIQ,2000,4.60\r\n"
        "PO-26-002,Karan Acids & Solvents,RM-SOLVENT-X,400,\r\n"
        "PO-26-003,Unknown Supplier Ltd,RM-HARD-AMN,100,9.00"
    ),
    "client_orders.csv": (
        "Client,Project,Target_Date,Product,Vol,Price\r\n"
        "Rohan Construction,PRJ-Mumbai-Mall,2026-08-15,SRV-INSTALL,12000,"
    ),
    "messy_partners.csv": (
        "Company_Name,Role,City,Contact\r\n"
        "Rohan Construction,Customer,Mumbai,Rohan"
    ),
}


def _meta_for(files: dict) -> dict:
    from containers.implementation.file_io.manifest_utils import build_file_meta
    return build_file_meta(files)


def test_score_manifest_detects_signals():
    meta = _meta_for(GREEN_SURFACE_FILES)
    result = score_manifest(
        filenames=list(GREEN_SURFACE_FILES.keys()),
        file_meta=meta,
        file_contents=GREEN_SURFACE_FILES,
    )
    assert result["signal_count"] > 0
    assert result["top_niche"]
    assert "manufacturing_project_chemical" in result["niche_scores"]


def test_green_surface_not_classified_as_garment():
    meta = _meta_for(GREEN_SURFACE_FILES)
    result = score_manifest(
        filenames=list(GREEN_SURFACE_FILES.keys()),
        file_meta=meta,
        file_contents=GREEN_SURFACE_FILES,
    )
    assert result["top_niche"] != "manufacturing_garment_variants"


def test_broad_manufacturing_discovery_prior_resolves_chemical():
    meta = _meta_for(GREEN_SURFACE_FILES)
    base = score_manifest(
        filenames=list(GREEN_SURFACE_FILES.keys()),
        file_meta=meta,
        file_contents=GREEN_SURFACE_FILES,
    )
    boosted = apply_discovery_prior(
        base,
        "manufacturing",
        discovery_industry="Chemical coatings and floor installation",
    )
    assert boosted.get("discovery_prior_applied")
    assert boosted["top_niche"] == "manufacturing_project_chemical"


def test_discovery_prior_boosts_niche():
    meta = _meta_for(GREEN_SURFACE_FILES)
    base = score_manifest(
        filenames=list(GREEN_SURFACE_FILES.keys()),
        file_meta=meta,
        file_contents=GREEN_SURFACE_FILES,
    )
    boosted = apply_discovery_prior(base, "manufacturing_project_chemical")
    assert boosted["niche_scores"]["manufacturing_project_chemical"] >= base["niche_scores"].get(
        "manufacturing_project_chemical", 0
    )


def test_prefer_discovery_over_garment_false_positive():
    from containers.implementation.signals_agent.signals_scorer import prefer_discovery_over_registry

    score_result = {
        "top_niche": "manufacturing_garment_variants",
        "niche_scores": {
            "manufacturing_garment_variants": 0.85,
            "manufacturing_project_chemical": 0.55,
        },
    }
    preferred = prefer_discovery_over_registry(
        score_result,
        discovery_f3iche="manufacturing",
        discovery_industry="Epoxy floor coatings manufacturer",
        chat_transcript="user: We manufacture coatings and do installation projects",
    )
    assert preferred == "manufacturing_project_chemical"


def test_blend_registry_wins_when_confident():
    registry = {
        "top_niche": "manufacturing_project_chemical",
        "confidence": 0.85,
        "confident": True,
    }
    f3iche, conf, method = blend_llm_with_registry(
        registry_result=registry,
        llm_f3iche="trading_fmcg_distributor",
        llm_confidence=0.9,
    )
    assert f3iche == "manufacturing_project_chemical"
    assert method == "registry_over_llm"


def test_blend_agrees_when_both_match():
    registry = {
        "top_niche": "manufacturing_project_chemical",
        "confidence": 0.7,
        "confident": True,
    }
    f3iche, conf, method = blend_llm_with_registry(
        registry_result=registry,
        llm_f3iche="manufacturing_project_chemical",
        llm_confidence=0.8,
    )
    assert f3iche == "manufacturing_project_chemical"
    assert method == "blended_agree"
    assert conf > 0.7
