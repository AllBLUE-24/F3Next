import unittest

from containers.implementation.mapping_agent.activities import _MappingEngine


class MappingEnginePartySplitTest(unittest.TestCase):
    def test_party_synonyms_support_alias_to_canonical_shape(self) -> None:
        engine = _MappingEngine()
        engine._field_mappings = {
            "party_type_synonyms": {
                "client": "Customer",
                "buyer": "Customer",
                "vendor": "Supplier",
                "seller": "Supplier",
            }
        }

        self.assertEqual(
            engine._get_party_type_synonyms(),
            {
                "Customer": ["client", "buyer", "customer"],
                "Supplier": ["vendor", "seller", "supplier"],
            },
        )

    def test_split_by_party_type_column(self) -> None:
        engine = _MappingEngine()
        engine._field_mappings = {
            "party_type_synonyms": {
                "client": "Customer",
                "buyer": "Customer",
                "vendor": "Supplier",
                "seller": "Supplier",
            }
        }

        rows = [
            {"party_type": "Customer", "party_name": "Apollo Hospitals", "territory": "India"},
            {"party_type": "Supplier", "party_name": "Dow Chemical Bulk", "territory": "Rest Of The World"},
        ]
        split = engine._split_by_entity_type(rows, ["party_type", "party_name", "territory"])

        self.assertEqual(set(split or {}), {"Customer", "Supplier"})
        self.assertEqual(len((split or {}).get("Customer", [])), 1)
        self.assertEqual(len((split or {}).get("Supplier", [])), 1)


if __name__ == "__main__":
    unittest.main()
