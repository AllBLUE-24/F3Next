"""P1 — file-level readiness (Step 8c) defers field gaps to Step 9 mapping."""
from __future__ import annotations

import os

from containers.implementation.data_readiness_agent.gap_analyzer import (
    analyze_gaps,
    readiness_file_level_only,
)
from containers.implementation.data_readiness_agent.file_doctype_matrix import (
    _corpus_claims_by_file,
)
from containers.implementation.file_io.enrich_corpus_understanding import (
    _extract_discovery_context,
)
from containers.implementation.file_io.manifest_utils import build_manifest_v2
from containers.implementation.mapping_agent.kb import field_mappings as _kb_field_mappings


def test_readiness_file_level_default_on():
    assert readiness_file_level_only() is True


def test_extract_discovery_context_from_chat():
    ctx = _extract_discovery_context(
        chat_history=[
            {"role": "user", "content": "We track chemical batch compliance for coatings projects."},
        ],
        discovery_metadata={"industry": "manufacturing", "pain_point": "batch traceability"},
    )
    assert "BUSINESS CONTEXT" in ctx
    assert "batch" in ctx.lower()
    assert "manufacturing" in ctx


def test_vendor_id_columns_file_level_ready():
    """Non-KB column names (VendorID) should not block readiness when corpus says Supplier."""
    files = {
        "vendors.csv": (
            "VendorID,Contact,Phone\r\n"
            "ACME-01,Jane Doe,555-0100\r\n"
            "BETA-02,John Smith,555-0200\r\n"
        ),
    }
    manifest = build_manifest_v2(files, created_at="2026-06-19T00:00:00Z")
    manifest["corpus_understanding"] = {
        "corpus_summary": "Vendor master list",
        "files": [
            {
                "filename": "vendors.csv",
                "likely_erpnext_doctypes": ["Supplier"],
            },
        ],
    }
    target = {
        "seed_doctypes": ["Supplier", "Customer"],
        "deferred_doctypes": [],
        "required_doctypes": ["Supplier", "Customer"],
        "setup_steps": [
            {"doctype": "Supplier", "phase": "phase_b_master", "action": "must_create"},
        ],
        "import_phases": {},
    }
    os.environ["IS_READINESS_FILE_LEVEL"] = "1"
    result = analyze_gaps(manifest, target, _kb_field_mappings())
    ready = {r["doctype"]: r for r in result["ready_doctypes"]}
    assert "Supplier" in ready
    assert ready["Supplier"].get("dry_run_exempt") or ready["Supplier"].get("field_gaps_deferred_to_mapping")


def test_missing_doctype_still_blocks_when_no_file():
    """File-level mode still reports missing when no file covers the seed doctype."""
    files = {
        "items.csv": "item_code,item_name\r\nSKU-1,Widget\r\n",
    }
    manifest = build_manifest_v2(files, created_at="2026-06-19T00:00:00Z")
    manifest["corpus_understanding"] = {
        "corpus_summary": "Item master only",
        "files": [{"filename": "items.csv", "likely_erpnext_doctypes": ["Item"]}],
    }
    target = {
        "seed_doctypes": ["Item", "Stock Entry"],
        "deferred_doctypes": [],
        "required_doctypes": ["Item", "Stock Entry"],
        "setup_steps": [],
        "import_phases": {},
    }
    os.environ["IS_READINESS_FILE_LEVEL"] = "1"
    result = analyze_gaps(manifest, target, _kb_field_mappings())
    missing = [m["doctype"] for m in result["missing_doctypes"]]
    assert "Stock Entry" in missing


def test_canonical_assignment_overrides_understanding_claim():
    claims = _corpus_claims_by_file(
        {
            "files": [{
                "filename": "parties.csv",
                "likely_erpnext_doctypes": ["Customer"],
            }],
        },
        {
            "version": 1,
            "assignments": [{
                "file": "parties.csv",
                "doctypes": ["Supplier"],
            }],
        },
    )
    assert claims == {"parties.csv": {"Supplier"}}
