"""Tests for tier-0 column header aliases (Tally exports)."""
import csv
import io
import unittest

from containers.implementation.mapping_agent.column_header_aliases import apply_header_aliases
from containers.implementation.mapping_agent.defaults import apply_defaults_and_normalize
from containers.implementation.mapping_agent.preflight_fields import preflight_mapped_records
from containers.knowledge_base.erpnext.schema.compose import clear_cache


class ColumnHeaderAliasesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        clear_cache()

    def test_tally_stock_summary_headers(self):
        cols = ["Name_of_Item", "Under_Group", "Base_Units"]
        mapping = apply_header_aliases(cols, "Item")
        self.assertEqual(mapping.get("Name_of_Item"), "item_code")
        self.assertEqual(mapping.get("Under_Group"), "item_group")
        self.assertEqual(mapping.get("Base_Units"), "stock_uom")

    def test_tally_sundry_ledgers_customer(self):
        cols = ["Ledger_Name", "Under_Group", "GSTIN"]
        mapping = apply_header_aliases(cols, "Customer")
        self.assertEqual(mapping.get("Ledger_Name"), "customer_name")

    def test_item_code_mirrors_item_name_before_preflight(self):
        rows = apply_defaults_and_normalize(
            "Item",
            [{"item_code": "FG-PRIMER-A", "item_group": "Finished Goods", "stock_uom": "Ltr"}],
        )
        self.assertEqual(rows[0]["item_name"], "FG-PRIMER-A")
        preflight = preflight_mapped_records("Item", rows)
        self.assertFalse(preflight.get("blocking"))

    def test_sundry_ledgers_customer_preflight(self):
        content = (
            "Ledger_Name,Under_Group\n"
            "Apollo Hospitals Enterprise,Sundry Debtors\n"
        )
        rows = list(csv.DictReader(io.StringIO(content)))
        mapping = apply_header_aliases(list(rows[0].keys()), "Customer")
        mapped = [
            {mapping[k]: v for k, v in row.items() if k in mapping}
            for row in rows
        ]
        mapped = apply_defaults_and_normalize("Customer", mapped)
        preflight = preflight_mapped_records("Customer", mapped)
        self.assertFalse(preflight.get("blocking"))


if __name__ == "__main__":
    unittest.main()
