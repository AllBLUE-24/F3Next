"""Unit tests for greenfield-aware live ERP readiness checks."""

from containers.implementation.data_readiness_agent.live_erp import (
    classify_empty_live_masters,
    file_covered_doctypes,
)


def test_file_covered_doctypes_from_ready_list():
    ready = [
        {"doctype": "Item", "source_file": "01_gs_master_items.csv"},
        {"doctype": "Customer", "source_file": "02_gs_parties.csv"},
        {"doctype": "Supplier", "source_file": "suppliers_list.csv"},
    ]
    covered = file_covered_doctypes(ready)
    assert covered == {"Item", "Customer", "Supplier"}


def test_empty_live_masters_covered_by_uploads_are_not_blocking():
    file_covered = {"Item", "Customer", "Supplier"}
    blocking, covered_by_import, gaps = classify_empty_live_masters(
        ["Customer", "Item", "Supplier"],
        file_covered,
    )
    assert blocking == []
    assert covered_by_import == ["Customer", "Item", "Supplier"]
    assert gaps == []


def test_empty_live_masters_without_uploads_stay_blocking():
    file_covered = {"Item", "Customer"}
    blocking, covered_by_import, gaps = classify_empty_live_masters(
        ["Customer", "Item", "Supplier"],
        file_covered,
    )
    assert blocking == ["Supplier"]
    assert covered_by_import == ["Customer", "Item"]
    assert len(gaps) == 1
    assert gaps[0]["doctype"] == "Supplier"
    assert gaps[0]["severity"] == "blocking"
    assert gaps[0]["rule_id"] == "is_live_erp_empty"
