"""Transactional party stub derivation — Green Surface 3rd_run shape."""
from __future__ import annotations

from containers.implementation.is_common.transactional_party_stubs import (
    derive_transactional_party_masters,
)


def _mapped_3rd_run_without_orphans():
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
                {"customer": "Rohan Construction", "items": [{"item_code": "SRV-INSTALL"}]},
                {"customer": "New Age Builders", "items": [{"item_code": "FG-PRIMER-A"}]},
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


def test_derive_new_age_customer_and_unknown_supplier():
    mapped = _mapped_3rd_run_without_orphans()
    enriched, audit = derive_transactional_party_masters(mapped)

    customer_names = {
        r.get("customer_name") for r in enriched["Customer"]["records"] if isinstance(r, dict)
    }
    supplier_names = {
        r.get("supplier_name") for r in enriched["Supplier"]["records"] if isinstance(r, dict)
    }

    assert "New Age Builders" in customer_names
    assert "Unknown Supplier Ltd" in supplier_names
    assert any(a["master_doctype"] == "Customer" for a in audit)
    assert any(a["master_doctype"] == "Supplier" for a in audit)


def test_derive_idempotent_when_master_already_present():
    mapped = _mapped_3rd_run_without_orphans()
    first, _ = derive_transactional_party_masters(mapped)
    second, audit = derive_transactional_party_masters(first)
    assert audit == []
    assert len(second["Customer"]["records"]) == len(first["Customer"]["records"])
