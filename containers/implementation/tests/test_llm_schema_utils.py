"""Tests for structured LLM JSON repair helpers."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from containers.implementation.file_io.corpus_models import CorpusUnderstanding
from shared.llm_schema_utils import build_structured_system_instruction, repair_pydantic_dict


def test_repair_missing_corpus_summary_from_files():
    raw = {
        "files": [
            {
                "filename": "client_orders.csv",
                "business_description": "Client project orders",
            }
        ]
    }
    repaired = repair_pydantic_dict(raw, CorpusUnderstanding)
    model = CorpusUnderstanding.model_validate(repaired)
    assert model.corpus_summary
    assert "Client project orders" in model.corpus_summary


def test_repair_summary_alias():
    raw = {"summary": "Chemical RM and project orders", "files": []}
    repaired = repair_pydantic_dict(raw, CorpusUnderstanding)
    model = CorpusUnderstanding.model_validate(repaired)
    assert model.corpus_summary == "Chemical RM and project orders"


def test_repair_column_interpretations_dict_to_list():
    raw = {
        "corpus_summary": "Batch upload",
        "files": [
            {
                "filename": "a.csv",
                "business_description": "Partners",
                "column_interpretations": {"Company_Name": "supplier or customer name"},
            }
        ],
    }
    repaired = repair_pydantic_dict(raw, CorpusUnderstanding)
    model = CorpusUnderstanding.model_validate(repaired)
    assert model.files[0].column_interpretations[0].column == "Company_Name"


def test_system_instruction_lists_required_keys():
    sys = build_structured_system_instruction(CorpusUnderstanding)
    assert "corpus_summary" in sys
    assert "files" in sys
