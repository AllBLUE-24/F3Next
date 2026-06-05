"""Tests for relative date default resolution."""
from __future__ import annotations

from containers.implementation.mapping_agent.defaults import apply_defaults_and_normalize


def test_delivery_date_derived_from_transaction_date():
    records = [{"customer": "Acme", "transaction_date": "2026-08-15"}]
    out = apply_defaults_and_normalize("Sales Order", records)
    assert out[0].get("delivery_date") == "2026-08-25"
