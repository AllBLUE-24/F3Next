"""Critical erp_semantics cases (mirrors OS business_fields tests)."""

from shared.erp_semantics import (
    build_transaction_title,
    business_fields_missing,
    clear_semantics_cache,
    is_master_create_doctype,
    merge_clarification_into_intent,
    resolve_company_for_payload,
    resolve_link_value_from_options,
)
from shared.os_field_semantics import is_master_create_doctype as shim_master


def setup_function() -> None:
    clear_semantics_cache()


def test_shim_reexports_match_canonical() -> None:
    assert shim_master("Sales Order") is False
    assert is_master_create_doctype("Customer") is True


def test_purchase_order_title_autofill_pattern() -> None:
    entities = {
        "supplier": "Acme Supplies",
        "items": [{"item_code": "RM-PIG-GRY", "qty": 1}],
    }
    title = build_transaction_title("Purchase Order", entities)
    assert title
    assert "acme" in title.casefold() or "RM" in title or "rm" in title.casefold()


def test_resolve_company_first_fallback() -> None:
    ctx = {
        "company_profile": {"company_name": "regww"},
        "link_cache": {"Company": ["Regww Pvt Ltd"]},
        "defaults": {},
    }
    resolved = resolve_company_for_payload("regww", ctx)
    assert resolved == "Regww Pvt Ltd"


def test_resolve_link_value_from_options_first_fallback() -> None:
    assert resolve_link_value_from_options(
        "regww",
        ["Regww Pvt Ltd"],
        allow_first_fallback=True,
    ) == "Regww Pvt Ltd"


def test_merge_clarification_title() -> None:
    partial = {
        "intent_id": "create_purchase_order",
        "target_doctype": "Purchase Order",
        "entities": {
            "supplier": "strahats",
            "items": [{"item_code": "RM-PIG-GRY", "qty": 1}],
        },
    }
    qa = [{
        "question": "I need a quick clarification to proceed: Field 'title' is mandatory for Purchase Order",
        "answer": "my-custom-title",
    }]
    out = merge_clarification_into_intent(partial, qa)
    assert out is not None
    assert out["entities"]["supplier"] == "strahats"
    assert out["entities"].get("title") == "my-custom-title"


def test_sales_order_no_erp_internal_missing() -> None:
    profile = {"company": "regww", "default_currency": "INR"}
    entities = {
        "customer": "bauli baramati",
        "items": [{"item_code": "PRIMER-BASE", "qty": 50}],
    }
    missing, _ = business_fields_missing("Sales Order", entities, profile)
    fields = {m["field"] for m in missing}
    assert "naming_series" not in fields
    assert "title" not in fields
