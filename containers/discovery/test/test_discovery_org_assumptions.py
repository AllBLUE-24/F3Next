"""Tests for org-structure assumption detection (F5)."""

from __future__ import annotations

from containers.discovery.discovery_org_assumptions import (
    open_org_assumptions,
    org_assumption_summary,
)

COMPLETE_ORG_TRANSCRIPT = (
    "We run a single factory site with 2 branches and 1 warehouse. "
    "Fiscal year is April to March. Opening balance cutover is 1 April. "
    "Single company in INR, no multi-currency."
)

BARE_TRANSCRIPT = "We manufacture adhesives and use Tally for accounting."


def test_open_org_assumptions_flags_all_four_when_unstated():
    open_items = open_org_assumptions(BARE_TRANSCRIPT)
    ids = {item["id"] for item in open_items}
    assert ids == {"locations", "fiscal_year", "opening_balance", "multi_company"}


def test_open_org_assumptions_empty_when_all_stated():
    assert open_org_assumptions(COMPLETE_ORG_TRANSCRIPT) == []


def test_org_assumption_summary_complete_flag():
    incomplete = org_assumption_summary(BARE_TRANSCRIPT)
    assert incomplete["assumptions_complete"] is False
    assert len(incomplete["open_assumptions"]) == 4

    complete = org_assumption_summary(COMPLETE_ORG_TRANSCRIPT)
    assert complete["assumptions_complete"] is True
    assert complete["open_assumptions"] == []
