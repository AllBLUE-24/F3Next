"""LER unit tests (no live ERP)."""

import pytest

from shared.erp_adapters.link_resolver import resolve_single
from shared.entity_resolution.gaps import resolution_gaps_from_unresolved
from shared.entity_resolution.ler import BRAIN_VERSION, apply_resolved_to_intent
from shared.entity_resolution.resolve import ResolvedEntities, resolve_entities_batch
from shared.entity_resolution.snapshot import brain_snapshot_keys, empty_brain_overlay
from shared.entity_resolution.targets import collect_link_targets_from_intent
from shared.gate_contracts import GapItem


def test_resolve_single_suffix_match() -> None:
    known = ["Work In Progress - GS", "Finished Goods - GS"]
    res = resolve_single("WIP", known, preferred_abbr="GS")
    assert res.resolved == "Work In Progress - GS"


def test_resolve_single_exact() -> None:
    known = ["bauli baramati", "Other Customer"]
    res = resolve_single("bauli baramati", known)
    assert res.resolved == "bauli baramati"
    assert not res.ambiguous


def test_resolve_entities_batch_company_list() -> None:
    link_cache = {
        "Company": ["Regww Pvt Ltd", "Regww"],
        "Customer": ["bauli baramati"],
        "Item": ["PRIMER-BASE"],
    }
    raw = {
        "customer": "bauli baramati",
        "company": "regww",
        "items": [{"item_code": "PRIMER-BASE", "qty": 1}],
    }
    resolved = resolve_entities_batch(raw, link_cache)
    assert resolved.customer == "bauli baramati"
    assert resolved.company in ("Regww Pvt Ltd", "Regww")
    assert resolved.items[0]["item_code"] == "PRIMER-BASE"


def test_collect_link_targets_from_intent_sales_order() -> None:
    intent = {
        "target_doctype": "Sales Order",
        "entities": {
            "customer": "bauli baramati",
            "items": [{"item_code": "FG-PRIMER-A", "qty": 10}],
        },
    }
    targets = collect_link_targets_from_intent(intent, "Sales Order")
    assert "Customer" in targets
    assert "bauli baramati" in targets["Customer"]
    assert "Item" in targets
    assert "FG-PRIMER-A" in targets["Item"]


def test_resolution_gaps_blocking_when_no_candidates() -> None:
    resolved = ResolvedEntities(unresolved={"customer": ["unknown-xyz"]})
    gaps = resolution_gaps_from_unresolved(resolved, link_cache={"Customer": []})
    assert len(gaps) == 1
    assert gaps[0].severity == "blocking"
    assert "unknown-xyz" in gaps[0].question


def test_resolution_gaps_choice_when_fuzzy_match() -> None:
    resolved = ResolvedEntities(unresolved={"customer": ["bauli"]})
    gaps = resolution_gaps_from_unresolved(
        resolved,
        link_cache={"Customer": ["bauli baramati", "bauli pune"]},
    )
    assert gaps[0].severity == "choice"
    assert len(gaps[0].candidates) >= 1


def test_apply_resolved_to_intent() -> None:
    from shared.erp_adapters.link_resolver import ResolutionMap

    intent = {
        "target_doctype": "Sales Order",
        "entities": {"customer": "bauli", "items": [{"item_code": "X", "qty": 1}]},
    }
    rmap = ResolutionMap(
        resolved={"Customer": {"bauli": "bauli baramati"}},
    )
    index = {"customer": "Customer"}
    out = apply_resolved_to_intent(intent, rmap, link_field_index=index)
    assert out["entities"]["customer"] == "bauli baramati"


def test_brain_snapshot_contract() -> None:
    keys = brain_snapshot_keys()
    assert "link_cache" in keys
    overlay = empty_brain_overlay()
    assert overlay["brain_version"] == BRAIN_VERSION


def test_import_public_api() -> None:
    from shared.entity_resolution import (
        build_link_cache,
        resolve_entities_batch,
        resolve_links_for_command,
    )

    assert callable(build_link_cache)
    assert callable(resolve_entities_batch)
    assert callable(resolve_links_for_command)
