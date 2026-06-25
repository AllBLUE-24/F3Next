"""KB default_value template resolution."""
from __future__ import annotations

from containers.implementation.mapping_agent.defaults import _resolve_default_value


def test_resolve_brace_template_from_record():
    record = {"supplier_name": "Gupta Chemical Traders"}
    assert _resolve_default_value(
        "Purchase Order",
        "title",
        "{supplier_name}",
        record=record,
    ) == "Gupta Chemical Traders"
