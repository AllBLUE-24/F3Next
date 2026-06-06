"""File×doctype matrix and corpus overclaim detection."""
from __future__ import annotations

from containers.implementation.data_readiness_agent.file_doctype_matrix import (
    assess_file_doctype_matrix,
)
from containers.implementation.data_readiness_agent.gap_analyzer import (
    _filename_prior_boost,
    _keyword_score_text,
    _score_columns_vs_doctype,
)
from containers.implementation.file_io.corpus_validation import detect_corpus_overclaims
from containers.implementation.mapping_agent.kb import field_mappings as _kb_field_mappings

THIRD_RUN_FILES = {
    "client_orders.csv": (
        "Client,Project,Target_Date,Product,Vol,Price\r\n"
        "Rohan Construction,PRJ-Mumbai-Mall,2026-08-15,SRV-INSTALL,12000,\r\n"
    ),
}


def test_matrix_marks_so_provable_on_client_orders():
    kb = _kb_field_mappings()
    file_meta = {
        "client_orders.csv": {
            "filename": "client_orders.csv",
            "columns": ["Client", "Project", "Target_Date", "Product", "Vol", "Price"],
            "is_structured": True,
            "content_snippet": "",
        },
    }
    corpus = {
        "files": [{
            "filename": "client_orders.csv",
            "likely_erpnext_doctypes": ["Sales Order", "Task"],
        }],
    }
    matrix = assess_file_doctype_matrix(
        files=THIRD_RUN_FILES,
        file_meta=file_meta,
        scope_doctypes=["Sales Order", "Task"],
        field_mappings_kb=kb,
        corpus_understanding=corpus,
        score_columns_fn=_score_columns_vs_doctype,
        keyword_score_fn=_keyword_score_text,
        filename_boost_fn=_filename_prior_boost,
    )
    rows = { (r["filename"], r["doctype"]): r for r in matrix["rows"] }
    so = rows[("client_orders.csv", "Sales Order")]
    assert so["evidenced"] is True
    assert so["field_provable"] is True
    task = rows[("client_orders.csv", "Task")]
    assert task["corpus_overclaim"] is True
    assert task["evidenced"] is False


def test_detect_corpus_overclaims_from_matrix():
    matrix = {
        "overclaims": [{
            "filename": "client_orders.csv",
            "doctype": "Task",
            "reason": "Corpus claimed Task without evidence",
        }],
    }
    warnings = detect_corpus_overclaims(matrix)
    assert len(warnings) == 1
    assert warnings[0]["code"] == "CORPUS_OVERCLAIM"
