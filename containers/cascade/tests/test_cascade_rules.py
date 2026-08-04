"""Tests for cascade rule matching and risk classification."""

from containers.cascade.rule_resolver.kb_loader import match_rules
from shared.erp_policies.action_risk import classify_cascade_risk, is_high_value_transaction


def test_match_sales_order_submit_rules():
    rules = match_rules("Sales Order", "on_submit")
    rule_ids = {r["rule_id"] for r in rules}
    assert "so_submitted_production" in rule_ids
    assert "so_submitted_accounts" in rule_ids


def test_match_unknown_doctype_returns_empty():
    assert match_rules("Quotation", "on_submit") == []


def test_classify_cascade_cancel_is_critical():
    assert classify_cascade_risk("Sales Order", "on_cancel") == "critical"


def test_high_value_transaction_detection():
    assert is_high_value_transaction("Sales Order", {"grand_total": 600000}) is True
    assert is_high_value_transaction("Sales Order", {"grand_total": 1000}) is False
