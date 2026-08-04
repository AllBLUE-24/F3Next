"""Supervisor chat contract + user-note resolution tests."""
from __future__ import annotations

from containers.implementation.is_common.ler_greenfield import (
    corpus_reference_values,
    session_covers_link_value,
)
from containers.implementation.is_common.transactional_party_stubs import (
    inject_party_master_stub,
)
from containers.implementation.supervisor_agent.chat_contract import (
    build_supervisor_extra_data,
    chat_must_signal_supervisor,
    is_blocking_supervisor_prompt,
    open_blocking_prompts,
)
from containers.implementation.supervisor_agent.user_note_resolutions import (
    apply_resolutions_to_mapped_data,
    parse_user_note_resolutions,
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


def test_blocking_supervisor_prompt_validation_not_mapping():
    assert is_blocking_supervisor_prompt({
        "step": "validation",
        "actions": [{"type": "ask_user", "id": "ask_user_ler_blocking_links"}],
    })
    assert not is_blocking_supervisor_prompt({
        "step": "mapping",
        "actions": [{"type": "ask_user", "id": "ask_user_map"}],
    })


def test_chat_must_signal_when_blocking_prompt_open():
    ctx = {
        "open_supervisor_prompts": [
            {
                "id": "p1",
                "step": "validation",
                "actions": [{"type": "ask_user", "id": "ask_user_ler_blocking_links"}],
            }
        ]
    }
    assert chat_must_signal_supervisor(ctx)
    assert len(open_blocking_prompts(ctx)) == 1


def test_build_supervisor_extra_data_free_text_sets_apply_flag():
    prompt = {
        "actions": [{
            "type": "ask_user",
            "id": "ask_user_ler_blocking_links",
            "options": [],
            "metadata": {"sample_gaps": [{"field": "company"}]},
        }]
    }
    note = """Here are the resolutions:
1. Company: Green Surface Limited
2. Customer Group: Commercial Contractors
3. Supplier: default vendor is Aditya Chemicals Ltd
"""
    extra = build_supervisor_extra_data(note, prompt)
    assert extra.get("apply_user_note") is True
    assert extra.get("user_note") == note.strip()
    assert extra.get("sample_gaps") == [{"field": "company"}]


def test_build_supervisor_extra_data_upload_intent():
    prompt = {
        "actions": [{
            "type": "ask_user",
            "id": "ask_user_missing_mvp_files",
            "options": ["Upload the missing files", "Review first"],
        }]
    }
    extra = build_supervisor_extra_data("", prompt, upload_intent=True)
    assert extra.get("upload_intent") is True
    assert str(extra.get("selected_option", "")).lower().startswith("upload")


def test_parse_user_note_resolutions_heuristic():
    note = """
1. Company: Green Surface Limited
2. Customer Group: Commercial Contractors
4. Supplier: For Purchase Receipts without a supplier, default vendor is "Aditya Chemicals Ltd".
- Raw Material Store: "Raw Material Store - GSL"
product_master.xlsx -> Item
warehouse_list.xlsx -> Warehouse
"""
    parsed = parse_user_note_resolutions(note, sample_gaps=[])
    assert any(s.get("name") == "Green Surface Limited" for s in parsed.get("party_stubs", []))
    assert any(r.get("doctype") == "Item" for r in parsed.get("file_doctype_rules", []))
    assert parsed.get("warehouse_aliases", {}).get("raw material store") == "Raw Material Store - GSL"


def test_apply_resolutions_fills_empty_supplier():
    mapped = {
        "Purchase Receipt": {
            "records": [{"supplier": "", "posting_date": "2026-01-01"}],
        },
        "Supplier": {"records": []},
    }
    resolutions = parse_user_note_resolutions(
        'default vendor is "Aditya Chemicals Ltd".',
        sample_gaps=[],
    )
    updated, audit = apply_resolutions_to_mapped_data(mapped, resolutions)
    assert updated["Purchase Receipt"]["records"][0]["supplier"] == "Aditya Chemicals Ltd"
    assert any(a.get("op") == "party_stub" for a in audit)
