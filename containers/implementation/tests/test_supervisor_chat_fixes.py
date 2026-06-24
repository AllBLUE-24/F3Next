"""Supervisor chat-first + LER greenfield fixes."""
from __future__ import annotations

from containers.implementation.is_common.ler_greenfield import (
    corpus_reference_values,
    session_covers_link_value,
)
from containers.implementation.is_common.transactional_party_stubs import (
    inject_party_master_stub,
)


def test_corpus_reference_covers_customer_on_sales_order_rows():
    mapped = {
        "Sales Order": {
            "records": [
                {"customer": "Larsen & Toubro Ltd", "items": [{"item_code": "FG-PRIMER-A"}]},
            ],
        },
    }
    assert "larsen & toubro ltd" in corpus_reference_values(mapped, "Customer")
    assert session_covers_link_value(
        mapped,
        link_target="Customer",
        value="Larsen & Toubro Ltd",
    )


def test_inject_party_master_stub_adds_customer():
    mapped = {"Customer": {"records": []}}
    updated, changed = inject_party_master_stub(
        mapped,
        master_doctype="Customer",
        name="Larsen & Toubro Ltd",
    )
    assert changed is True
    names = {r.get("customer_name") for r in updated["Customer"]["records"]}
    assert "Larsen & Toubro Ltd" in names


def test_chat_create_master_extraction():
    from backend.app.services.is_chat_dispatcher import _extract_create_master

    action = {
        "metadata": {
            "sample_gaps": [
                {
                    "metadata": {"target_doctype": "Customer", "value": "Larsen & Toubro Ltd"},
                }
            ],
        },
    }
    out = _extract_create_master("create the customer - Larsen & Toubro Ltd", action)
    assert out is not None
    assert out["doctype"] == "Customer"
    assert "Larsen" in out["name"]


def test_chat_link_value_regex_does_not_match_bare_it():
    from backend.app.services.is_chat_dispatcher import _LINK_VALUE_ANSWER

    assert _LINK_VALUE_ANSWER.search("add it to the erpnext site") is None
