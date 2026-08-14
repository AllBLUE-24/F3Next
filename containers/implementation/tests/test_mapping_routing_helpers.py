"""Unit tests for mapping routing helpers (corpus + assignment + readiness)."""
import asyncio
import csv
import io
import unittest
from unittest.mock import AsyncMock, patch

from containers.implementation.mapping_agent.activities import (
    _MappingEngine,
    _assignment_includes_doctype,
    _corpus_likely_doctype,
    _filename_doctype_override,
    _get_candidate_doctypes,
    _norm_filename,
    _readiness_file_doctype_evidence,
    _resolve_structured_file_doctype,
)


class MappingRoutingHelpersTest(unittest.TestCase):
    def test_corpus_likely_doctype_single_match(self):
        hints = {"filename": "tally_stock_summary.csv", "likely_erpnext_doctypes": ["Item"]}
        self.assertEqual(_corpus_likely_doctype(hints, ["Item", "BOM"]), "Item")

    def test_corpus_likely_doctype_ambiguous_returns_none(self):
        hints = {"likely_erpnext_doctypes": ["Item", "BOM"]}
        self.assertIsNone(_corpus_likely_doctype(hints, ["Item", "BOM"]))

    def test_assignment_includes_doctype(self):
        assignment = {"file": "tally_sundry_ledgers.csv", "doctypes": ["Customer", "Supplier"]}
        self.assertTrue(_assignment_includes_doctype(assignment, "Customer"))
        self.assertTrue(_assignment_includes_doctype(assignment, "Supplier"))
        self.assertFalse(_assignment_includes_doctype(assignment, "Item"))

    def test_assignment_split_includes_doctype(self):
        assignment = {
            "file": "messy.csv",
            "doctypes": ["Customer", "Supplier"],
            "split": {
                "Customer": {"doctype": "Customer", "rows": 2},
                "Supplier": {"doctype": "Supplier", "rows": 1},
            },
        }
        self.assertTrue(_assignment_includes_doctype(assignment, "Supplier"))

    def test_readiness_file_doctype_evidence_matrix_row(self):
        class _Row:
            gap_report = {
                "file_doctype_matrix": {
                    "rows": [
                        {
                            "filename": "tally_stock_summary.csv",
                            "doctype": "Item",
                            "evidenced": True,
                        }
                    ]
                }
            }

        self.assertTrue(
            _readiness_file_doctype_evidence(
                _Row(),
                "tally_stock_summary.csv",
                "Item",
            )
        )

    def test_norm_filename(self):
        self.assertEqual(_norm_filename(" Foo.CSV "), "foo.csv")

    def test_filename_doctype_override_stock_summary(self):
        self.assertEqual(_filename_doctype_override("tally_stock_summary.csv"), "Item")

    def test_candidates_are_bounded_by_confirmed_target(self):
        with patch(
            "containers.implementation.mapping_agent.activities._load_session_required_doctypes",
            new=AsyncMock(return_value=["BOM", "Work Order"]),
        ):
            candidates = asyncio.run(_get_candidate_doctypes("unused"))

        self.assertEqual(candidates, ["BOM", "Work Order"])
        self.assertNotIn("Customer", candidates)

    def test_canonical_assignment_beats_filename_prior(self):
        resolved = asyncio.run(
            _resolve_structured_file_doctype(
                filename="tally_stock_summary.csv",
                columns=["party_name"],
                candidates=["Customer", "Item"],
                user_note="",
                corpus_hints=None,
                corpus_assignment={"doctypes": ["Customer"]},
                doctype_hint=None,
            )
        )

        self.assertEqual(resolved, "Customer")

    def test_tally_sundry_ledgers_party_split(self):
        content = (
            "Ledger_Name,Under_Group\n"
            "Apollo Hospitals Enterprise,Sundry Debtors\n"
            "Dow Chemical International,Sundry Creditors\n"
        )
        rows = list(csv.DictReader(io.StringIO(content)))
        columns = list(rows[0].keys())
        engine = _MappingEngine()
        groups = engine._split_by_entity_type(rows, columns)
        self.assertIsNotNone(groups)
        self.assertIn("Customer", groups)
        self.assertIn("Supplier", groups)
        self.assertEqual(len(groups["Customer"]), 1)
        self.assertEqual(len(groups["Supplier"]), 1)


if __name__ == "__main__":
    unittest.main()
