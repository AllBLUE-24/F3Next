"""OS validator — company slug guard from link_resolution_policy."""

from containers.os.validation_agent.validator import validate_payload_bundle


def test_blocks_company_slug_as_company():
    bundle = {
        "steps": [{
            "step_number": 1,
            "action": "create",
            "doctype": "Sales Order",
            "payload": {
                "company": "green-surface",
                "customer": "Test Customer",
                "items": [{"item_code": "ITEM-1", "qty": 1}],
            },
        }],
    }
    context = {
        "company_slug": "green-surface",
        "company_profile": {"entity_registry": {"known_customers": ["Test Customer"], "known_items": ["ITEM-1"]}},
        "doctype_schema": {"mandatory_fields": [], "field_mappings": {}, "child_tables": {}},
        "intent": {"entities": {}},
    }
    result = validate_payload_bundle(bundle, context)
    company_errors = [e for e in result["errors"] if e.get("field") == "company"]
    assert company_errors
    assert "slug" in company_errors[0]["message"].casefold()
