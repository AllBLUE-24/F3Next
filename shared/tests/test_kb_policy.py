"""KB policy spine — loaders, preflight, IS import rules."""

from __future__ import annotations

import pytest

from shared.kb.policy_loaders import (
    clear_policy_caches,
    get_execution_preflight_rules,
    get_is_import_rules,
    get_link_resolution_policy,
    get_os_validation_config,
)


@pytest.fixture(autouse=True)
def _clear_caches():
    clear_policy_caches()
    yield
    clear_policy_caches()


def test_os_validation_has_business_fields():
    cfg = get_os_validation_config()
    assert "erp_autofill_fields" in cfg
    assert cfg.get("company_resolution_policy")
    bfb = cfg.get("business_fields_by_doctype") or {}
    assert "Purchase Order" in bfb
    assert "supplier" in bfb["Purchase Order"]


def test_is_import_rules_primary_fields():
    rules = get_is_import_rules()
    req = rules.get("required_fields_by_doctype") or {}
    assert "Item" in req
    assert "item_code" in req["Item"]
    assert rules.get("messages", {}).get("missing_required_field")


def test_execution_preflight_rules_loaded():
    rules = get_execution_preflight_rules()
    ids = {r.get("id") for r in rules}
    assert "po_subcontract_item" in ids
    assert "po_supplier_exists" in ids


def test_link_resolution_policy():
    pol = get_link_resolution_policy()
    assert pol.get("company_resolution", {}).get("policy")
    assert pol.get("is_link_missing_message")


def test_preflight_subcontract_blocks_non_subcontract_item():
    import asyncio
    from shared.kb.preflight import evaluate_execution_preflight

    class FakeAdapter:
        async def get_record(self, doctype, name):
            if doctype == "Supplier":
                return {"name": name, "is_sub_contractor": 1}
            if doctype == "Item":
                return {"name": name, "is_sub_contracted_item": 0}
            return {}

        async def list_records(self, *a, **k):
            return []

    errors = asyncio.run(evaluate_execution_preflight(
        FakeAdapter(),
        "Purchase Order",
        {
            "supplier": "SubCo",
            "items": [{"item_code": "PART-1", "qty": 1}],
        },
    ))
    assert errors
    assert "PART-1" in errors[0]
    assert "sub-contracted" in errors[0].casefold()


def test_preflight_company_invalid():
    import asyncio
    from shared.kb.preflight import evaluate_execution_preflight

    class FakeAdapter:
        async def get_record(self, *a, **k):
            return {}

        async def list_records(self, doctype, fields, **k):
            if doctype == "Company":
                return [{"name": "Acme Ltd"}]
            return []

    errors = asyncio.run(evaluate_execution_preflight(
        FakeAdapter(),
        "Sales Order",
        {"company": "Not-A-Company", "customer": "C1"},
    ))
    assert errors
    assert "Not-A-Company" in errors[0]
