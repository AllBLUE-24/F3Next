"""Unit tests for mapping routing helpers (corpus + assignment + readiness)."""
import unittest

from containers.implementation.mapping_agent.activities import (
    _assignment_includes_doctype,
    _corpus_likely_doctype,
    _norm_filename,
    _readiness_file_doctype_evidence,
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


if __name__ == "__main__":
    unittest.main()
