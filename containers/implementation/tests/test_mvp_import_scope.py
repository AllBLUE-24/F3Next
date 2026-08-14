"""MVP import scope — finalize blocking aligns with bottleneck seeds."""
from __future__ import annotations

from types import SimpleNamespace

from containers.implementation.import_agent.mvp_import_scope import (
    blocking_unmapped_seeds,
    is_out_of_mvp_scope,
    parse_mvp_scope_from_target,
    project_target_scope_data,
)


def test_parse_mvp_scope_from_target():
    seeds, deferred = parse_mvp_scope_from_target({
        "seed_doctypes": ["Customer", "Sales Order", "Stock Entry"],
        "deferred_doctypes": ["BOM", "Work Order"],
    })
    assert "Customer" in seeds
    assert "Sales Order" in seeds
    assert "BOM" in deferred


def test_project_target_scope_falls_back_to_postgres_columns():
    project_target = SimpleNamespace(
        target_structure_json={},
        seed_doctypes=["BOM", "Work Order"],
        deferred_doctypes=["Job Card"],
    )

    seeds, deferred = parse_mvp_scope_from_target(
        project_target_scope_data(project_target)
    )

    assert seeds == {"BOM", "Work Order"}
    assert deferred == {"Job Card"}


def test_item_project_out_of_mvp_scope():
    seeds = {"Customer", "Sales Order", "Purchase Order"}
    deferred: set = set()
    assert is_out_of_mvp_scope("Item", seeds, deferred)
    assert is_out_of_mvp_scope("Project", seeds, deferred)
    assert is_out_of_mvp_scope("BOM", seeds, deferred)
    assert not is_out_of_mvp_scope("Stock Entry", {"Stock Entry"}, deferred)


def test_blocking_unmapped_only_mvp_seeds():
    seeds = ["Customer", "Supplier", "Sales Order", "Stock Entry"]
    mapped = {"Customer", "Supplier", "Sales Order"}
    blocking = blocking_unmapped_seeds(seeds, mapped, set())
    assert blocking == ["Stock Entry"]

    # Item missing from graph but not in MVP seeds — does not block
    blocking2 = blocking_unmapped_seeds(
        seeds,
        mapped,
        set(),
    )
    assert "Item" not in blocking2
