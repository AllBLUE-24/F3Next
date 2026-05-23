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


if __name__ == "__main__":
    unittest.main()
