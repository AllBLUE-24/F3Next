"""Out-of-scope Link field mapping policy."""
from __future__ import annotations

from containers.implementation.is_common.link_scope_policy import filter_field_mapping
from containers.implementation.mapping_agent.dry_run_map import dry_run_map_file
from containers.implementation.mapping_agent.kb import field_mappings as _kb_field_mappings
from containers.implementation.tests.test_dry_run_map_3rd_run import THIRD_RUN_FILES


def test_contact_column_not_mapped_to_customer_primary_contact():
    kb = _kb_field_mappings()
    result = dry_run_map_file(
        THIRD_RUN_FILES["messy_partners.csv"],
        "Customer",
        kb=kb,
    )
    assert "Contact" not in result["field_mapping"]
    assert "customer_primary_contact" not in result["field_mapping"].values()


def test_contact_link_kept_when_contact_in_scope():
    kb = _kb_field_mappings()
    mapping = {
        "Company_Name": "customer_name",
        "Contact": "customer_primary_contact",
    }
    filtered, stripped = filter_field_mapping(
        mapping,
        "Customer",
        kb,
        scoped_doctypes={"Customer", "Contact"},
    )
    assert filtered.get("Contact") == "customer_primary_contact"
    assert not stripped
