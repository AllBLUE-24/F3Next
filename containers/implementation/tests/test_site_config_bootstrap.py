"""Tests for Site Config Bootstrap (SCB) — Phase 1."""
import unittest

from containers.implementation.is_common.import_preview import build_import_preview
from containers.implementation.is_common.ler_greenfield import classify_ler_unresolvable
from containers.implementation.is_common.site_config_bootstrap import (
    bootstrap_site_config,
    collect_distinct_link_values,
    derive_config_records,
    phase_0_steps_from_bootstrap,
    resolve_config_value,
)
from containers.implementation.mapping_agent.value_translation import fuzzy_match_live_erp
from containers.knowledge_base.erpnext.schema.compose import clear_cache


class SiteConfigBootstrapTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        clear_cache()

    def test_collect_distinct_item_groups(self):
        mapped = {
            "Item": {
                "records": [
                    {"item_code": "A", "item_group": "Raw Materials"},
                    {"item_code": "B", "item_group": "Finished Goods"},
                    {"item_code": "C", "item_group": "Raw Materials"},
                ]
            }
        }
        distinct = collect_distinct_link_values(mapped)
        self.assertIn("Raw Materials", distinct["Item Group"])
        self.assertIn("Finished Goods", distinct["Item Group"])

    def test_fuzzy_match_raw_materials_plural(self):
        match = fuzzy_match_live_erp("Raw Materials", ["Raw Material", "Finished Goods"])
        self.assertEqual(match, "Raw Material")

    def test_resolve_config_value_fuzzy(self):
        resolved, rule = resolve_config_value(
            "Raw Materials",
            config_doctype="Item Group",
            link_cache={"Item Group": ["Raw Material", "Finished Goods"]},
        )
        self.assertEqual(resolved, "Raw Material")
        self.assertEqual(rule, "live_erp_fuzzy")

    def test_derive_missing_item_group(self):
        mapped = {
            "Item": {
                "records": [{"item_code": "A", "item_group": "Custom Alloy Mix"}],
            }
        }
        derived, audit = derive_config_records(
            mapped,
            link_cache={"Item Group": ["Raw Material"]},
        )
        self.assertIn("Item Group", derived)
        names = [r["item_group_name"] for r in derived["Item Group"]["records"]]
        self.assertIn("Custom Alloy Mix", names)
        self.assertTrue(any(a.get("rule_id") == "scb_derive_config" for a in audit))

    def test_bootstrap_patches_plural_to_singular(self):
        mapped = {
            "Item": {
                "records": [{"item_code": "A", "item_group": "Raw Materials"}],
            }
        }
        summary = bootstrap_site_config(
            mapped,
            link_cache={"Item Group": ["Raw Material"]},
        )
        items = summary["mapped_data"]["Item"]["records"]
        self.assertEqual(items[0]["item_group"], "Raw Material")
        self.assertNotIn("Item Group", summary.get("derived_doctypes") or [])

    def test_ler_greenfield_defers_when_bootstrap_covers(self):
        mapped = {
            "Item": {"records": [{"item_code": "A", "item_group": "Custom Alloy Mix"}]},
            "Item Group": {
                "records": [{"item_group_name": "Custom Alloy Mix"}],
                "source": "site_config_bootstrap",
            },
        }
        disposition, _msg = classify_ler_unresolvable(
            {
                "doctype": "Item",
                "field": "item_group",
                "value": "Custom Alloy Mix",
                "target_doctype": "Item Group",
            },
            mapped,
        )
        self.assertEqual(disposition, "info")

    def test_phase_0_steps_order(self):
        derived = {
            "Customer Group": {"records": [{"customer_group_name": "Local"}]},
            "Item Group": {"records": [{"item_group_name": "Raw Material"}]},
        }
        steps = phase_0_steps_from_bootstrap(derived)
        doctypes = [s["doctype"] for s in steps]
        self.assertEqual(doctypes[0], "Item Group")
        self.assertEqual(steps[0]["action"], "create")

    def test_import_preview_splits_hints_and_blocking(self):
        preview = build_import_preview(
            ler_gaps=[
                {
                    "severity": "hint",
                    "field": "customer",
                    "doctype": "Sales Order",
                    "question": "Customer X will be created",
                    "metadata": {"link_target": "Customer", "value": "Apollo"},
                },
                {
                    "severity": "blocking",
                    "field": "item_group",
                    "doctype": "Item",
                    "question": "Item Group missing",
                    "metadata": {"link_target": "Item Group", "value": "Unknown"},
                },
            ],
            mapped_data={"Item": {"records": [{}]}},
        )
        self.assertEqual(len(preview["will_create_on_erp"]), 1)
        self.assertEqual(len(preview["needs_your_ok"]), 1)


if __name__ == "__main__":
    unittest.main()
