import unittest

from containers.implementation.mapping_agent.activities import _MappingEngine
from containers.implementation.mapping_agent.corpus_merge import (
    aggregate_mapped_data_rows,
    filename_conflicts_with_doctype,
    filename_implied_doctype,
    filter_quarantined_records,
    inject_missing_mapped_steps,
    merge_payloads,
    merge_record_lists,
)


class _MappedRow:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


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


class CorpusMergeTest(unittest.TestCase):
    def test_merge_suppliers_dedupes_by_name(self) -> None:
        existing = [
            {"supplier_name": "Dow Chemical Bulk", "country": "USA"},
            {"supplier_name": "Local Sands & Aggregates"},
        ]
        incoming = [
            {"supplier_name": "Apex Resins Pvt Ltd"},
            {"supplier_name": "Dow Chemical Bulk", "gstin": "27AAAAA0000A1Z5"},
        ]
        merged = merge_record_lists("Supplier", existing, incoming)
        names = {r["supplier_name"] for r in merged}
        self.assertEqual(len(merged), 3)
        self.assertIn("Dow Chemical Bulk", names)
        dow = next(r for r in merged if r["supplier_name"] == "Dow Chemical Bulk")
        self.assertEqual(dow.get("gstin"), "27AAAAA0000A1Z5")

    def test_merge_payloads_unions_records(self) -> None:
        out = merge_payloads(
            "Supplier",
            {"doctype": "Supplier", "records": [{"supplier_name": "A"}]},
            {"doctype": "Supplier", "link_fields": {"x": "Y"}, "records": [{"supplier_name": "B"}]},
        )
        self.assertEqual(len(out["records"]), 2)
        self.assertEqual(out["link_fields"], {"x": "Y"})

    def test_aggregate_mapped_data_rows(self) -> None:
        rows = [
            _MappedRow(
                target_doctype="Supplier",
                mapped_payload_r2_path="gs/p1/mappings/mapped_payloads/Supplier.json",
                total_rows=2,
                validation_status="pending",
                source_filename="parties.csv",
            ),
            _MappedRow(
                target_doctype="Supplier",
                mapped_payload_r2_path="gs/p1/mappings/mapped_payloads/Supplier.json",
                total_rows=4,
                validation_status="passed",
                source_filename="suppliers_list.csv",
            ),
        ]
        agg = aggregate_mapped_data_rows(rows)
        self.assertEqual(agg["Supplier"]["total_rows"], 6)
        self.assertEqual(len(agg["Supplier"]["source_files"]), 2)

    def test_inject_missing_project_step(self) -> None:
        phases = {
            "phase_b_master": {"name": "Master Data", "steps": [{"doctype": "Item", "action": "create"}]},
            "phase_c_transactional": {"name": "Transactional", "steps": []},
        }
        mapped = {
            "Project": {"r2_path": "gs/p1/mappings/mapped_payloads/Project.json", "total_rows": 2},
        }
        updated = inject_missing_mapped_steps(phases, mapped)
        project_steps = updated["phase_d_projects"]["steps"]
        self.assertEqual(len(project_steps), 1)
        self.assertEqual(project_steps[0]["doctype"], "Project")

    def test_quarantine_empty_supplier_identity(self) -> None:
        rows = [
            {"supplier_name": "Apex Chemicals Ltd."},
            {"supplier_group": "All Supplier Groups"},
            {"customer_name": "Apollo Hospitals", "supplier_group": "All Supplier Groups"},
        ]
        kept, quarantined = filter_quarantined_records("Supplier", rows)
        self.assertEqual(len(kept), 1)
        self.assertEqual(len(quarantined), 2)
        self.assertEqual(kept[0]["supplier_name"], "Apex Chemicals Ltd.")

    def test_merge_skips_anonymous_rows(self) -> None:
        existing = [{"supplier_name": "Dow Chemical Bulk"}]
        incoming = [
            {"supplier_group": "All Supplier Groups"},
            {"supplier_name": "Apex Chemicals Ltd."},
        ]
        merged = merge_record_lists("Supplier", existing, incoming)
        self.assertEqual(len(merged), 2)
        names = {r["supplier_name"] for r in merged}
        self.assertEqual(names, {"Dow Chemical Bulk", "Apex Chemicals Ltd."})

    def test_active_projects_filename_implies_project(self) -> None:
        implied = filename_implied_doctype("05_gs_active_projects.csv")
        self.assertEqual(implied, "Project")
        self.assertTrue(filename_conflicts_with_doctype("05_gs_active_projects.csv", "Purchase Receipt"))
        self.assertFalse(filename_conflicts_with_doctype("05_gs_active_projects.csv", "Project"))


class DefaultsInjectionTest(unittest.TestCase):
    def test_injects_naming_series_for_project(self) -> None:
        from containers.implementation.mapping_agent.defaults import apply_defaults_and_normalize

        out = apply_defaults_and_normalize("Project", [{"project_name": "Green Surface Site A"}])
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].get("naming_series"), "PROJ-")
        self.assertEqual(out[0].get("project_name"), "Green Surface Site A")

    def test_does_not_overwrite_existing_naming_series(self) -> None:
        from containers.implementation.mapping_agent.defaults import apply_defaults_and_normalize

        out = apply_defaults_and_normalize(
            "Project",
            [{"project_name": "Site A", "naming_series": "CUSTOM-"}],
        )
        self.assertEqual(out[0].get("naming_series"), "CUSTOM-")

    def test_normalize_mapped_payload_injects_naming_series(self) -> None:
        from containers.implementation.mapping_agent.defaults import normalize_mapped_payload

        payload = {"doctype": "Project", "records": [{"project_name": "Site B"}]}
        out = normalize_mapped_payload("Project", payload)
        self.assertEqual(out["records"][0].get("naming_series"), "PROJ-")


if __name__ == "__main__":
    unittest.main()
