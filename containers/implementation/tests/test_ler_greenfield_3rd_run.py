"""LER greenfield — Green Surface 3rd_run validation report shape."""
from __future__ import annotations

from containers.implementation.is_common.ler_greenfield import (
    classify_ler_unresolvable,
    resolve_link_target_doctype,
    session_covers_link_value,
    transactional_reference_values,
)
from containers.implementation.validation_agent.activities import _ValidationEngine


def _mapped_3rd_run():
    """Minimal mapped_data mirroring r2_files.json payloads."""
    return {
        "Customer": {
            "records": [
                {"customer_name": "Rohan Construction"},
                {"customer_name": "Ultra Floors Pvt Ltd"},
            ],
        },
        "Supplier": {
            "records": [
                {"supplier_name": "Gupta Chemical Traders"},
                {"supplier_name": "Karan Acids & Solvents"},
            ],
        },
        "Sales Order": {
            "records": [
                {
                    "customer": "Rohan Construction",
                    "project": "PRJ-Mumbai-Mall",
                    "items": [{"item_code": "SRV-INSTALL", "qty": 12000}],
                },
                {
                    "customer": "New Age Builders",
                    "project": "PRJ-Pune-ITPark",
                    "items": [{"item_code": "FG-PRIMER-A", "qty": 200}],
                },
            ],
        },
        "Purchase Order": {
            "records": [
                {"supplier": "Gupta Chemical Traders", "items": [{"item_code": "RM-EPOX-LIQ"}]},
                {"supplier": "Karan Acids & Solvents", "items": [{"item_code": "RM-SOLVENT-X"}]},
                {"supplier": "Unknown Supplier Ltd", "items": [{"item_code": "RM-HARD-AMN"}]},
            ],
        },
    }


def test_resolve_link_target_from_target_doctype():
    assert resolve_link_target_doctype({"target_doctype": "Customer"}) == "Customer"


def test_resolve_link_target_from_field_name():
    assert resolve_link_target_doctype({"field": "customer"}) == "Customer"
    assert resolve_link_target_doctype({"field": "supplier"}) == "Supplier"
    assert resolve_link_target_doctype({"field": "project"}) == "Project"


def test_transactional_refs_cover_new_age_and_unknown_supplier():
    mapped = _mapped_3rd_run()
    assert session_covers_link_value(
        mapped, link_target="Customer", value="New Age Builders",
    )
    assert session_covers_link_value(
        mapped, link_target="Supplier", value="Unknown Supplier Ltd",
    )
    assert "new age builders" in transactional_reference_values(mapped, "Customer")
    assert "unknown supplier ltd" in transactional_reference_values(mapped, "Supplier")


def test_ler_hit_with_field_customer_deferred_for_rohan():
    mapped = _mapped_3rd_run()
    disposition, msg = classify_ler_unresolvable(
        {
            "doctype": "Sales Order",
            "field": "customer",
            "target_doctype": "Customer",
            "value": "Rohan Construction",
        },
        mapped,
    )
    assert disposition == "info"
    assert "master import" in msg.lower()


def test_contact_link_stays_blocking():
    mapped = _mapped_3rd_run()
    disposition, _ = classify_ler_unresolvable(
        {
            "doctype": "Customer",
            "field": "customer_primary_contact",
            "target_doctype": "Contact",
            "value": "Rohan",
        },
        mapped,
    )
    assert disposition == "blocking"


def test_merge_ler_assigns_errors_to_source_doctype_not_unknown():
    mapped = _mapped_3rd_run()
    engine = _ValidationEngine(graph={}, field_mappings={})
    base_report = {
        "overall": "pass",
        "checks": [
            {"doctype": "Sales Order", "status": "pass", "errors": [], "warnings": [], "row_count": 2},
            {"doctype": "Customer", "status": "pass", "errors": [], "warnings": [], "row_count": 2},
            {"doctype": "Supplier", "status": "pass", "errors": [], "warnings": [], "row_count": 2},
            {"doctype": "Purchase Order", "status": "pass", "errors": [], "warnings": [], "row_count": 3},
        ],
        "errors": [],
        "warnings": [],
    }
    ler_report = {
        "unresolvable_values": [
            {
                "doctype": "Sales Order",
                "field": "customer",
                "target_doctype": "Customer",
                "value": "Rohan Construction",
            },
            {
                "doctype": "Sales Order",
                "field": "customer",
                "target_doctype": "Customer",
                "value": "New Age Builders",
            },
            {
                "doctype": "Customer",
                "field": "customer_primary_contact",
                "target_doctype": "Contact",
                "value": "Rohan",
            },
        ],
    }
    report = engine.merge_ler_unresolvable(base_report, ler_report, mapped_data=mapped)

    # SO LER hits deferred (greenfield); Contact link on Customer stays blocking → overall fail
    assert report["overall"] == "fail"
    so = next(c for c in report["checks"] if c["doctype"] == "Sales Order")
    assert so["status"] == "pass"
    assert len(so["warnings"]) == 0
    assert not any(c["doctype"] == "Unknown" for c in report["checks"])
    cust = next(c for c in report["checks"] if c["doctype"] == "Customer")
    assert cust["status"] == "fail"
    assert any("Rohan" in e for e in cust["errors"])
