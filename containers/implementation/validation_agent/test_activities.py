import unittest

from containers.implementation.validation_agent.activities import _ValidationEngine


class ValidationEngineEnumParsingTest(unittest.TestCase):
    def test_select_options_from_list(self) -> None:
        engine = _ValidationEngine(
            field_mappings={
                "doctypes": {
                    "Work Order": {
                        "field_mappings": {
                            "status": {
                                "fieldname": "status",
                                "fieldtype": "Select",
                                "options": ["Draft", "Submitted", "Completed"],
                            }
                        }
                    }
                }
            }
        )

        self.assertEqual(
            engine._get_enum_rules("Work Order"),
            {"status": ["Draft", "Submitted", "Completed"]},
        )

    def test_select_options_from_json_string(self) -> None:
        engine = _ValidationEngine(
            field_mappings={
                "doctypes": {
                    "Work Order": {
                        "field_mappings": {
                            "status": {
                                "fieldname": "status",
                                "fieldtype": "Select",
                                "options": '["Draft", "Submitted", "Completed"]',
                            }
                        }
                    }
                }
            }
        )

        self.assertEqual(
            engine._get_enum_rules("Work Order"),
            {"status": ["Draft", "Submitted", "Completed"]},
        )


class ValidationPartialStatusTest(unittest.TestCase):
    def test_doctype_partial_when_warnings_only(self) -> None:
        engine = _ValidationEngine()
        report = engine.validate(
            {"Item": {"records": []}},
            {"required_doctypes": ["Item"], "validation_rules": {}},
        )
        item_check = next(c for c in report["checks"] if c["doctype"] == "Item")
        self.assertEqual(item_check["status"], "partial")
        self.assertEqual(report["overall"], "partial")

    def test_doctype_fail_when_required_value_empty(self) -> None:
        engine = _ValidationEngine()
        report = engine.validate(
            {
                "Supplier": {
                    "records": [
                        {
                            "supplier_name": "",
                            "supplier_group": "All Supplier Groups",
                            "supplier_type": "Company",
                        }
                    ]
                }
            },
            {"required_doctypes": ["Supplier"], "validation_rules": {}},
        )
        supplier_check = next(c for c in report["checks"] if c["doctype"] == "Supplier")
        self.assertEqual(supplier_check["status"], "fail")
        self.assertEqual(report["overall"], "fail")

    def test_purchase_order_fails_when_items_empty(self) -> None:
        engine = _ValidationEngine(
            graph={
                "doctypes": {
                    "Purchase Order": {
                        "required_fields": ["supplier", "items (item_code, qty, rate)", "transaction_date"],
                    }
                }
            }
        )
        report = engine.validate(
            {
                "Purchase Order": {
                    "records": [
                        {
                            "supplier": "Gupta Chemical Traders",
                            "transaction_date": "2026-01-01",
                            "items": [],
                        }
                    ]
                }
            },
            {"required_doctypes": ["Purchase Order"], "validation_rules": {}},
        )
        po_check = next(c for c in report["checks"] if c["doctype"] == "Purchase Order")
        self.assertEqual(po_check["status"], "fail")
        self.assertTrue(any("items" in str(e).lower() for e in po_check["errors"]))


class ValidationReportEnrichmentTest(unittest.TestCase):
    def test_enrich_checks_with_sources(self) -> None:
        from shared.models.validation_report import enrich_checks_with_sources, normalize_validation_report

        report = {
            "overall": "pass",
            "checks": [{"doctype": "Supplier", "status": "pass", "errors": [], "warnings": [], "row_count": 2}],
        }
        enriched = enrich_checks_with_sources(
            report,
            {"Supplier": ["vendors.csv", "suppliers_extra.csv"]},
        )
        check = enriched["checks"][0]
        self.assertEqual(check["source_files"], ["vendors.csv", "suppliers_extra.csv"])

        normalized = normalize_validation_report(enriched)
        self.assertIsNotNone(normalized)
        assert normalized is not None
        self.assertEqual(normalized["checks"][0]["source_files"], ["vendors.csv", "suppliers_extra.csv"])


if __name__ == "__main__":
    unittest.main()
