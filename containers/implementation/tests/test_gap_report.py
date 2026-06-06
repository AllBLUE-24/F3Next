"""Unified gap report builders."""
from __future__ import annotations

from containers.implementation.is_common.gap_report import (
    gap_from_preflight_block,
    gaps_from_pre_analysis,
    open_critical_gaps,
)
from containers.implementation.is_common.ler_greenfield import (
    classify_ler_unresolvable,
    session_covers_link_value,
)


def test_preflight_block_gap():
    gap = gap_from_preflight_block({
        "doctype": "Purchase Order",
        "source_file": "raw_purchase_orders.csv",
        "missing_fields": ["items"],
        "messages": ["Required field 'items' is missing"],
    })
    assert gap.doctype == "Purchase Order"
    assert gap.metadata["origin"] == "mapping_preflight"
    assert gap.metadata["tier"] == "critical"


def test_dry_run_failure_in_pre_analysis_gaps():
    pre = {
        "partial_doctypes": [{
            "doctype": "Purchase Order",
            "source_file": "raw_purchase_orders.csv",
            "dry_run_failed": True,
            "dry_run": {"missing_required_after": ["items"]},
        }],
        "missing_doctypes": [],
    }
    items = gaps_from_pre_analysis(pre)
    assert len(items) == 1
    assert items[0]["doctype"] == "Purchase Order"


def test_ler_greenfield_covered_by_session_batch():
    mapped = {
        "Customer": {
            "records": [
                {"customer_name": "Rohan Construction"},
            ],
        },
    }
    assert session_covers_link_value(
        mapped, link_target="Customer", value="Rohan Construction",
    )
    disposition, msg = classify_ler_unresolvable(
        {
            "doctype": "Sales Order",
            "field": "customer",
            "link_target": "Customer",
            "value": "Rohan Construction",
        },
        mapped,
    )
    assert disposition == "info"
    assert "master import" in msg.lower()


def test_open_critical_gaps_filters_info():
    items = [
        {"severity": "hint", "metadata": {"tier": "info"}},
        {"severity": "blocking", "metadata": {"tier": "critical"}},
    ]
    assert len(open_critical_gaps(items)) == 1
