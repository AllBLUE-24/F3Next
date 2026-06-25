"""Import phase ordering and link alias tests."""

from shared.erp_adapters.link_resolver import build_alias_lookup
from containers.implementation.import_agent.phase_order import sort_phases


def test_sort_phases_runs_projects_before_transactional():
    phases = {
        "phase_c_transactional": {"name": "Transactional Data", "steps": []},
        "phase_d_projects": {"name": "Project Data", "steps": []},
        "phase_b_master": {"name": "Master Data", "steps": []},
        "phase_a_config": {"name": "Configuration Setup", "steps": []},
        "phase_0_site_config": {"name": "Site Config Bootstrap", "steps": []},
    }
    ordered = [pid for pid, _ in sort_phases(phases)]
    assert ordered.index("phase_d_projects") < ordered.index("phase_c_transactional")


def test_build_alias_lookup_project_name_to_docname():
    alias_map = build_alias_lookup(
        [
            {"name": "PROJ-0004", "project_name": "PRJ-Apollo-ICU-Floor"},
            {"name": "PROJ-0003", "project_name": "PRJ-L&T-Hangar-Coating"},
        ],
        alt_field="project_name",
    )
    assert alias_map["PRJ-Apollo-ICU-Floor"] == "PROJ-0004"
    assert alias_map["PRJ-L&T-Hangar-Coating"] == "PROJ-0003"
    assert alias_map["PROJ-0004"] == "PROJ-0004"
