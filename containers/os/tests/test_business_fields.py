"""Tests for OS business-field semantics (no ERP-internal user prompts)."""
from shared.os_field_semantics import (
    apply_business_clarification_answers,
    apply_computed_defaults_to_payload,
    apply_profile_autofill_to_payload,
    build_transaction_title,
    business_fields_missing,
    clear_semantics_cache,
    is_master_create_doctype,
    is_skip_answer,
    merge_clarification_into_intent,
    parse_natural_date,
    preserve_transaction_entities,
    resolve_link_value_from_options,
)


def setup_function() -> None:
    clear_semantics_cache()


def test_sales_order_is_not_master_create() -> None:
    assert is_master_create_doctype("Customer") is True
    assert is_master_create_doctype("Sales Order") is False
    assert is_master_create_doctype("Purchase Order") is False


def test_sales_order_does_not_ask_erp_internal_fields() -> None:
    profile = {
        "company": "regww",
        "default_currency": "INR",
        "default_price_list": "Standard Selling",
    }
    entities = {
        "customer": "bauli baramati",
        "items": [{"item_code": "PRIMER-BASE", "qty": 50}],
    }
    missing, applied = business_fields_missing("Sales Order", entities, profile)
    fields = {m["field"] for m in missing}
    assert "naming_series" not in fields
    assert "conversion_rate" not in fields
    assert "selling_price_list" not in fields
    assert "customer" not in fields
    assert "items" not in fields
    assert any(m["field"] == "delivery_date" and m["tier"] == 2 for m in missing)
    assert any(a["field"] == "currency" for a in applied)


def test_delivery_date_skip_phrases() -> None:
    assert is_skip_answer("not needed")
    assert is_skip_answer("naah")
    assert not is_skip_answer("2026-06-15")


def test_parse_natural_date_5th_june_uses_current_year() -> None:
    from datetime import date
    y = date.today().year
    assert parse_natural_date("5th june", default_year=y) == f"{y}-06-05"
    assert parse_natural_date("5 june", default_year=y) == f"{y}-06-05"


def test_merge_clarification_preserves_items_and_customer() -> None:
    partial = {
        "intent_id": "create_sales_order",
        "target_doctype": "Sales Order",
        "entities": {
            "customer": "bauli baramati",
            "items": [{"item_code": "FG-PRIMER-A", "qty": 50, "uom": "Gallon"}],
        },
    }
    qa = [{"question": "When should this order be delivered?", "answer": "5th june"}]
    out = merge_clarification_into_intent(partial, qa)
    assert out is not None
    assert out["entities"]["customer"] == "bauli baramati"
    assert out["entities"]["items"][0]["item_code"] == "FG-PRIMER-A"
    from datetime import date
    y = date.today().year
    assert out["entities"]["delivery_date"] == f"{y}-06-05"
    assert "supplier" not in out["entities"]


def test_preserve_transaction_entities_after_bad_llm_shape() -> None:
    partial = {
        "intent_id": "create_sales_order",
        "target_doctype": "Sales Order",
        "entities": {
            "customer": "bauli baramati",
            "items": [{"item_code": "FG-PRIMER-A", "qty": 50}],
        },
    }
    bad = {
        "intent_id": "create_sales_order",
        "target_doctype": "Sales Order",
        "entities": {
            "customer": "bauli",
            "supplier": "primer base",
            "delivery_date": "2023-06-05",
            "items": [{"item_name": "primer base", "quantity": 50}],
        },
    }
    fixed = preserve_transaction_entities(bad, partial, "Sales Order")
    assert fixed["entities"]["customer"] == "bauli baramati"
    assert fixed["entities"]["items"][0]["item_code"] == "FG-PRIMER-A"
    assert "supplier" not in fixed["entities"]


def test_apply_profile_autofill_to_payload() -> None:
    payload = {
        "company": "user_default_company_or_first_company",
        "currency": "fetch_from_customer_or_company_default",
        "customer": "bauli baramati",
    }
    ctx = {
        "company_profile": {
            "company": "regww",
            "default_currency": "INR",
            "default_price_list": "Standard Selling",
        }
    }
    out = apply_profile_autofill_to_payload("Sales Order", payload, ctx)
    assert out["company"] == "regww"
    assert out["currency"] == "INR"
    assert out["selling_price_list"] == "Standard Selling"
    assert out.get("naming_series")
    assert out.get("conversion_rate") == 1.0


def test_purchase_order_title_autofill_supplier_item() -> None:
    entities = {
        "supplier": "Apex Chemicals Ltd.",
        "items": [{"item_code": "RM-PIG-GRY", "qty": 100, "uom": "Kg"}],
    }
    title = build_transaction_title("Purchase Order", entities)
    assert title == "apex-chemicals-ltd-rm-pig-gry"

    payload = {
        "supplier": "Apex Chemicals Ltd.",
        "items": [{"item_code": "RM-PIG-GRY", "qty": 100}],
        "company": "user_default_company_or_first_company",
    }
    ctx = {
        "company_profile": {"company_name": "strahats"},
        "link_cache": {"Company": ["Strahats Pvt Ltd"]},
        "defaults": {},
    }
    out = apply_computed_defaults_to_payload("Purchase Order", payload, entities, ctx)
    assert out.get("title") == "apex-chemicals-ltd-rm-pig-gry"
    assert out.get("company") == "Strahats Pvt Ltd"


def test_resolve_link_value_first_company_fallback() -> None:
    assert resolve_link_value_from_options(
        "user_default_company_or_first_company",
        ["Acme Corp", "Other"],
        allow_first_fallback=True,
    ) == "Acme Corp"
    assert resolve_link_value_from_options("Acme Corp", ["Acme Corp"]) == "Acme Corp"


def test_merge_clarification_maps_title_field() -> None:
    partial = {
        "intent_id": "create_purchase_order",
        "target_doctype": "Purchase Order",
        "entities": {
            "supplier": "Apex Chemicals Ltd.",
            "items": [{"item_code": "RM-PIG-GRY", "qty": 100}],
        },
    }
    qa = [{
        "question": "I need a quick clarification to proceed: Field 'title' is mandatory for Purchase Order",
        "answer": "PO-apex-dry pigment",
    }]
    out = merge_clarification_into_intent(partial, qa)
    assert out is not None
    assert out["entities"].get("title") == "PO-apex-dry pigment"
    assert out["entities"]["supplier"] == "Apex Chemicals Ltd."


def test_preserve_transaction_entities_purchase_strips_customer() -> None:
    partial = {
        "target_doctype": "Purchase Order",
        "entities": {
            "supplier": "Apex Chemicals Ltd.",
            "items": [{"item_code": "RM-PIG-GRY", "qty": 100}],
        },
    }
    bad = {
        "target_doctype": "Purchase Order",
        "entities": {
            "supplier": "Apex Chemicals",
            "customer": "Apex Chemicals",
            "items": [{"item_code": "RM-PIG-GRY", "qty": 100}],
        },
    }
    fixed = preserve_transaction_entities(bad, partial, "Purchase Order")
    assert fixed["entities"]["supplier"] == "Apex Chemicals Ltd."
    assert "customer" not in fixed["entities"]


def test_apply_business_clarification_skip_delivery() -> None:
    intent = {
        "intent_id": "create_sales_order",
        "entities": {"customer": "Acme", "items": [{"item_code": "X", "qty": 1}]},
    }
    qa = [{
        "question": "When should this order be delivered? (Optional — say skip)",
        "answer": "not needed",
    }]
    out = apply_business_clarification_answers(intent, qa)
    assert out["entities"]["delivery_date"] is None
    assert out["entities"]["extra"]["delivery_date_skipped"] is True
