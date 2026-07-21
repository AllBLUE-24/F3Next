"""Tests for promotion reason parsing."""

from __future__ import annotations

from containers.discovery.promotion_reasons import promotion_reasons_from_notes


def test_parses_promoted_note_lines():
    notes = [
        "Promoted Job Card — shop-floor routing/yield costing requires operation tracking.",
        "Promoted Stock Entry — Work Order is Day-1; ERPNext manufacture loop requires it.",
        "Deferred Sales Invoice — accounting stays in legacy system.",
    ]
    reasons = promotion_reasons_from_notes(notes)
    assert reasons["Job Card"].startswith("shop-floor routing")
    assert "Stock Entry" in reasons
    assert "Sales Invoice" not in reasons
