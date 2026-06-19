"""P2 — session learnings, live schema merge, dry-run LLM flag."""
from __future__ import annotations

import os
from unittest.mock import AsyncMock, patch

import pytest

from containers.implementation.mapping_agent.dry_run_map import (
    _dry_run_llm_enabled,
    dry_run_map_file,
)
from containers.implementation.mapping_agent.mapping_learnings import (
    apply_learnings_to_kb,
    collect_successful_learnings,
    merge_learnings,
)
from containers.implementation.mapping_agent.schema_resolver import (
    merge_live_schema_into_kb,
    resolve_kb_gaps_async,
)


def test_collect_successful_learnings_skips_kb_local():
    items = collect_successful_learnings(
        doctype="Supplier",
        source_file="vendors.csv",
        field_mapping={"VendorID": "supplier_name", "supplier_name": "supplier_name"},
        methods={"VendorID": "llm_column_map", "supplier_name": "kb_local"},
    )
    assert len(items) == 1
    assert items[0]["source_column"] == "VendorID"
    assert items[0]["erp_field"] == "supplier_name"


def test_apply_learnings_adds_runtime_synonym():
    kb = {
        "doctypes": {
            "Supplier": {
                "field_mappings": {
                    "supplier_name": {
                        "fieldname": "supplier_name",
                        "user_input_synonyms": ["supplier"],
                    },
                },
            },
        },
    }
    learnings = [{
        "doctype": "Supplier",
        "source_column": "VendorID",
        "erp_field": "supplier_name",
        "method": "llm_column_map",
    }]
    patched = apply_learnings_to_kb(kb, "Supplier", learnings)
    syns = patched["doctypes"]["Supplier"]["field_mappings"]["supplier_name"]["user_input_synonyms"]
    assert "VendorID" in syns


def test_merge_learnings_dedupes():
    a = [{"doctype": "Item", "source_column": "SKU", "erp_field": "item_code"}]
    b = [{"doctype": "Item", "source_column": "SKU", "erp_field": "item_code"}]
    merged = merge_learnings(a, b)
    assert len(merged) == 1


def test_merge_live_schema_into_kb_creates_doctype():
    live = [
        {
            "fieldname": "quotation_to",
            "fieldtype": "Link",
            "mandatory": True,
            "user_input_synonyms": ["quotation_to", "customer"],
        },
    ]
    kb: dict = {"doctypes": {}}
    patched, meta = merge_live_schema_into_kb("Quotation", kb, live)
    assert meta["live_merged"] is True
    assert "Quotation" in patched["doctypes"]
    assert "quotation_to" in patched["doctypes"]["Quotation"]["field_mappings"]


def test_resolve_kb_gaps_async_merges_live_for_kb_miss():
    import asyncio

    kb = {"doctypes": {}}
    live_fields = [{
        "fieldname": "project_name",
        "fieldtype": "Data",
        "mandatory": True,
        "user_input_synonyms": ["project_name"],
    }]

    async def _run():
        with patch(
            "containers.implementation.mapping_agent.live_schema.fetch_live_doctype_schema",
            new=AsyncMock(return_value=live_fields),
        ):
            return await resolve_kb_gaps_async("Project", kb, project_id="test-project")

    patched, meta = asyncio.run(_run())
    assert meta.get("live_merged") is True
    assert "Project" in patched.get("doctypes", {})


def test_dry_run_llm_flag():
    os.environ["IS_DRY_RUN_LLM"] = "1"
    assert _dry_run_llm_enabled() is True
    os.environ["IS_DRY_RUN_LLM"] = "0"
    assert _dry_run_llm_enabled() is False


def test_dry_run_map_file_runs_with_llm_flag(monkeypatch):
    """Smoke: IS_DRY_RUN_LLM path delegates to async tiered mapper."""
    monkeypatch.setenv("IS_DRY_RUN_LLM", "1")

    async def _fake_async(*args, **kwargs):
        return {
            "passed": True,
            "field_mapping": {"VendorID": "supplier_name"},
            "preflight": {"blocking": False, "missing_fields": []},
            "record_count": 1,
            "methods": {"VendorID": "llm_column_map"},
            "missing_required_after": [],
            "schema_resolver": {},
            "synonym_promotions": [],
            "dry_run_mode": "tiered_llm",
        }

    monkeypatch.setattr(
        "containers.implementation.mapping_agent.dry_run_map.dry_run_map_file_async",
        _fake_async,
    )

    content = "VendorID\r\nACME\r\n"
    kb = {"doctypes": {}}
    result = dry_run_map_file(content, "Supplier", kb=kb)
    assert result.get("dry_run_mode") == "tiered_llm"
    assert result.get("passed") is True
