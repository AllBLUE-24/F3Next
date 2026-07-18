"""Tests for corpus manifest parsing (Step 2)."""
from __future__ import annotations

from containers.implementation.corpus.manifest import (
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


def test_parse_structured_csv_extracts_columns_and_samples():
    meta = parse_structured_content(CLIENT_ORDERS_CSV, "client_orders.csv")
    assert meta["is_structured"] is True
    assert "Client" in meta["columns"]
    assert meta["row_count"] == 2
    assert len(meta["sample_rows"]) == 2


def test_build_manifest_v2_shape():
    manifest = build_manifest_v2({"client_orders.csv": CLIENT_ORDERS_CSV}, created_at="2026-06-05T00:00:00Z")
    assert manifest["_manifest_version"] == 2
    assert manifest["file_count"] == 1
    assert manifest["file_meta"]["client_orders.csv"]["row_count"] == 2


def test_normalize_manifest_input_legacy_v1():
    legacy = {"a.csv": "x,y\n1,2"}
    files, meta, corpus = normalize_manifest_input(legacy)
    assert "a.csv" in files
    assert meta["a.csv"]["columns"] == ["x", "y"]
    assert corpus is None


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


def test_extract_files_from_manifest_v2():
    manifest = build_manifest_v2({"f.csv": "a\n1"}, created_at="t")
    files = extract_files_from_manifest(manifest)
    assert files == {"f.csv": "a\n1"}


def test_build_file_meta_matches_manifest_builder():
    contents = {"client_orders.csv": CLIENT_ORDERS_CSV}
    meta = build_file_meta(contents)
    manifest = build_manifest_v2(contents, created_at="t")
    assert meta["client_orders.csv"]["columns"] == manifest["file_meta"]["client_orders.csv"]["columns"]
