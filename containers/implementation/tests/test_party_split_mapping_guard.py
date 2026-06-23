"""Tests for party split field-mapping guard."""
import unittest

from containers.implementation.is_common.party_rules import strip_split_column_from_field_mapping


class PartySplitMappingGuardTest(unittest.TestCase):
    def test_strips_under_group_for_customer(self):
        mapping = {
            "Ledger_Name": "customer_name",
            "Under_Group": "customer_group",
            "GSTIN": "gstin",
        }
        cols = ["Ledger_Name", "Under_Group", "GSTIN"]
        out = strip_split_column_from_field_mapping(mapping, cols, "Customer")
        self.assertNotIn("Under_Group", out)
        self.assertEqual(out["Ledger_Name"], "customer_name")

    def test_no_change_for_item(self):
        mapping = {"Under_Group": "item_group"}
        out = strip_split_column_from_field_mapping(mapping, ["Under_Group"], "Item")
        self.assertEqual(out, mapping)


if __name__ == "__main__":
    unittest.main()
