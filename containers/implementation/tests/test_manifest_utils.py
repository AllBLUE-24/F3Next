"""Tests for manifest v2 parsing and corpus exclusion helpers."""
from __future__ import annotations

from containers.implementation.data_readiness_agent.gap_analyzer import analyze_gaps
from containers.implementation.file_io.manifest_utils import (
    build_file_meta,
    build_manifest_v2,
    corpus_exclusions_by_doctype,
    extract_files_from_manifest,
    normalize_manifest_input,
    parse_structured_content,
)


CLIENT_ORDERS_CSV = (
    "Client,Project,Target_Date,Product,Vol,Price\r\n"
    "Rohan Construction,PRJ-Mumbai-Mall,2026-08-15,SRV-INSTALL,12000,\r\n"
    "New Age Builders,PRJ-Pune-ITPark,2026-09-01,FG-PRIMER-A,200,52.00"
)

EMPLOYEES_CSV = (
    "names,department\r\n"
    "Parth Kulkarni,Production\r\n"
    "Manish Malotra,QC"
)


def test_parse_structured_csv_extracts_columns_and_samples():
    meta = parse_structured_content(CLIENT_ORDERS_CSV, "client_orders.csv")
    assert meta["is_structured"] is True
    assert "Client" in meta["columns"]
    assert meta["row_count"] == 2
    assert len(meta["sample_rows"]) == 2
    assert meta["sample_rows"][0]["Client"] == "Rohan Construction"


def test_build_manifest_v2_shape():
    contents = {"client_orders.csv": CLIENT_ORDERS_CSV}
    manifest = build_manifest_v2(contents, created_at="2026-06-05T00:00:00Z")
    assert manifest["_manifest_version"] == 2
    assert manifest["file_count"] == 1
    assert "file_meta" in manifest
    assert manifest["file_meta"]["client_orders.csv"]["row_count"] == 2


def test_normalize_manifest_input_legacy_v1():
    legacy = {"a.csv": "x,y\n1,2"}
    files, meta, corpus = normalize_manifest_input(legacy)
    assert "a.csv" in files
    assert meta["a.csv"]["columns"] == ["x", "y"]
    assert corpus is None


def test_extract_files_from_manifest_v2():
    manifest = build_manifest_v2({"f.csv": "a\n1"}, created_at="t")
    files = extract_files_from_manifest(manifest)
    assert files == {"f.csv": "a\n1"}


def test_corpus_exclusions_by_doctype():
    corpus = {
        "files": [
            {
                "filename": "client_orders.csv",
                "explicitly_not_doctypes": ["Work Order", "BOM"],
            }
        ]
    }
    exclusions = corpus_exclusions_by_doctype(corpus)
    assert "client_orders.csv" in exclusions["Work Order"]
    assert "client_orders.csv" in exclusions["BOM"]


def test_gap_analyzer_respects_corpus_exclusions():
    """client_orders.csv columns must not produce a Work Order partial match."""
    manifest = build_manifest_v2(
        {"client_orders.csv": CLIENT_ORDERS_CSV},
        created_at="2026-06-05T00:00:00Z",
    )
    manifest["corpus_understanding"] = {
        "corpus_summary": "Client project orders",
        "files": [
            {
                "filename": "client_orders.csv",
                "explicitly_not_doctypes": ["Work Order", "BOM"],
            }
        ],
    }
    target_structure = {
        "required_doctypes": ["Work Order", "BOM", "Customer"],
        "setup_steps": [
            {"doctype": "Work Order", "phase": "phase_c_transactional", "action": "must_create"},
            {"doctype": "BOM", "phase": "phase_b_master", "action": "must_create"},
            {"doctype": "Customer", "phase": "phase_b_master", "action": "must_create"},
        ],
        "import_phases": {},
    }
    kb = {"doctypes": {}, "doctype_keyword_hints": {}}

    result = analyze_gaps(manifest, target_structure, kb)
    partial_doctypes = [p["doctype"] for p in result["partial_doctypes"]]
    assert "Work Order" not in partial_doctypes


def test_parse_employees_names_column():
    meta = parse_structured_content(EMPLOYEES_CSV, "employees.csv")
    assert "names" in meta["columns"]
    assert meta["sample_rows"][0]["names"] == "Parth Kulkarni"
