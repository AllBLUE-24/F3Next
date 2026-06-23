"""Tests for Value Translation Layer (VTL) — Phase 0."""
import csv
import io
import json
import unittest
from pathlib import Path

from containers.implementation.is_common.party_rules import strip_split_column_from_field_mapping
from containers.implementation.mapping_agent.column_header_aliases import apply_header_aliases
from containers.implementation.mapping_agent.defaults import apply_defaults_and_normalize
from containers.implementation.mapping_agent.value_translation import apply_value_translations
from containers.knowledge_base.erpnext.schema.compose import clear_cache

_GOLDEN = Path(__file__).resolve().parents[3] / "attachments" / "green-surface" / "greensurface_golden_data" / "4th_run"


class ValueTranslationLayerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        clear_cache()

    def test_raw_materials_plural_to_singular(self):
        rows, audit = apply_value_translations(
            "Item",
            [{"item_code": "RM-1", "item_group": "Raw Materials", "stock_uom": "Kg"}],
        )
        self.assertEqual(rows[0]["item_group"], "Raw Material")
        self.assertTrue(any(a.get("rule_id") == "vtl_field_value_map" for a in audit))

    def test_sundry_debtors_dropped_from_customer_group(self):
        rows, audit = apply_value_translations(
            "Customer",
            [{"customer_name": "Apollo", "customer_group": "Sundry Debtors"}],
        )
        self.assertEqual(rows[0]["customer_group"], "All Customer Groups")
        self.assertTrue(any(a.get("rule_id") == "vtl_drop_party_ledger" for a in audit))

    def test_party_split_column_not_mapped_to_customer_group(self):
        cols = ["Ledger_Name", "Under_Group", "GSTIN"]
        mapping = apply_header_aliases(cols, "Customer")
        mapping["Under_Group"] = "customer_group"  # simulate fuzzy map
        stripped = strip_split_column_from_field_mapping(mapping, cols, "Customer")
        self.assertNotIn("Under_Group", stripped)
        self.assertEqual(stripped.get("Ledger_Name"), "customer_name")

    def test_sundry_ledgers_end_to_end_defaults(self):
        content = (
            "Ledger_Name,Under_Group\n"
            "Apollo Hospitals Enterprise,Sundry Debtors\n"
        )
        rows = list(csv.DictReader(io.StringIO(content)))
        cols = list(rows[0].keys())
        mapping = apply_header_aliases(cols, "Customer")
        mapping = strip_split_column_from_field_mapping(mapping, cols, "Customer")
        mapped = [{mapping[k]: v for k, v in row.items() if k in mapping} for row in rows]
        mapped = apply_defaults_and_normalize("Customer", mapped)
        self.assertEqual(mapped[0]["customer_group"], "All Customer Groups")

    def test_z_output_customer_payload_after_vtl(self):
        path = _GOLDEN / "Z_output.json"
        if not path.is_file():
            self.skipTest("Z_output.json not present")
        raw = path.read_text(encoding="utf-8")
        # File contains validation report + embedded customer JSON
        customer_block = raw.split("#customer.json", 1)[-1]
        payload = json.loads(customer_block.strip())
        rows, audit = apply_value_translations("Customer", payload.get("records") or [])
        groups = {r.get("customer_group") for r in rows}
        self.assertNotIn("Sundry Debtors", groups)
        self.assertIn("All Customer Groups", groups)
        self.assertGreaterEqual(len(audit), 2)

    def test_z_output_item_payload_raw_materials_translated(self):
        path = _GOLDEN / "Z_output.json"
        if not path.is_file():
            self.skipTest("Z_output.json not present")
        raw = path.read_text(encoding="utf-8")
        item_block = raw.split("#item.json", 1)[1].split("#customer.json", 1)[0]
        payload = json.loads(item_block.strip())
        rows, _audit = apply_value_translations("Item", payload.get("records") or [])
        rm_rows = [r for r in rows if r.get("item_group") == "Raw Material"]
        self.assertEqual(len(rm_rows), 3)


if __name__ == "__main__":
    unittest.main()
