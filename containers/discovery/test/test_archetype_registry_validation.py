"""Validation tests for archetype registry (interim Research merge gate)."""

from __future__ import annotations

from containers.discovery.archetype_registry import validate_archetype_registry

CHEMICAL_F3ICHE = "manufacturing_project_chemical"


def test_validate_current_catalog_and_chemical_f3iche_has_no_errors():
    result = validate_archetype_registry(CHEMICAL_F3ICHE)
    assert not result["errors"], result["errors"]
    assert result["archetype_count"] >= 10


def test_validate_catches_missing_archetype_id():
    bad = {"primary_bottleneck": "x", "day1_seed_hints": ["Item"], "signals": ["a", "b", "c"]}
    from containers.discovery.archetype_registry import _validate_archetype_entry

    errors, _ = _validate_archetype_entry(bad, source="test", graph_keys=frozenset(["Item"]))
    assert any("missing archetype_id" in e for e in errors)


def test_validate_catches_bad_id_format():
    bad = {
        "archetype_id": "Bad-Id",
        "primary_bottleneck": "x",
        "day1_seed_hints": ["Item"],
        "signals": ["a", "b", "c"],
    }
    from containers.discovery.archetype_registry import _validate_archetype_entry

    errors, _ = _validate_archetype_entry(bad, source="test", graph_keys=frozenset(["Item"]))
    assert any("snake_case" in e for e in errors)
