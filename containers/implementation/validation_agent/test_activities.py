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
