import unittest

from containers.implementation.mapping_agent.preview_flatten import flatten_records_for_preview


class PreviewFlattenTest(unittest.TestCase):
    def test_merges_first_child_item_onto_parent(self) -> None:
        records = [
            {
                "name": "STE-001",
                "stock_entry_type": "Material Receipt",
                "items": [{"item_code": "RM-001", "qty": 10, "uom": "Nos"}],
            }
        ]
        flat, columns = flatten_records_for_preview(records)
        self.assertEqual(flat[0].get("item_code"), "RM-001")
        self.assertEqual(flat[0].get("qty"), 10)
        self.assertIn("item_code", columns)
        self.assertNotIn("items", flat[0])


if __name__ == "__main__":
    unittest.main()
