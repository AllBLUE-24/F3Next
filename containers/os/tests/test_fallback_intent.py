"""Unit tests for Clarity keyword fallback (_fallback_intent)."""
from containers.os.clarity_agent.activities import _fallback_intent


def test_create_customer_dash_separator_extracts_name() -> None:
    out = _fallback_intent(
        "create a new customer - bauli baramati",
        "erpnext",
        "test",
    )
    assert out["intent_id"] == "create_customer"
    assert out["entities"]["customer"] == "bauli baramati"
    assert out["has_ambiguities"] is False


def test_create_customer_missing_name_adds_ambiguity() -> None:
    out = _fallback_intent("create a new customer", "erpnext", "test")
    assert out["intent_id"] == "create_customer"
    assert not out["entities"]["customer"]
    assert any(a.get("field") == "customer" for a in out["ambiguities"])
