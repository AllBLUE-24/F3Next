"""Test Clarity Agent - run from operation_agent directory."""
import json
import sys

sys.path.insert(0, ".")

from utils import parse_clarity_output


def test_parse_output():
    """Test JSON parsing without API call."""
    print("Test 1: Parse output (no API)")
    raw = '{"intent": "create_sales_order", "entities": {"customer": "ABC Industries", "items": [{"item": "Product-001", "qty": 100, "rate": 500}]}, "confidence": 0.95}'
    result = parse_clarity_output(raw)
    assert result["intent"] == "create_sales_order"
    assert result["entities"]["customer"] == "ABC Industries"
    assert len(result["entities"]["items"]) == 1
    assert result["entities"]["items"][0]["qty"] == 100
    print("  OK:", json.dumps(result, indent=2))
    print()


def test_clarity():
    """Test full Clarity Agent with API (requires Ollama running)."""
    from agents.clarity_agent import process_prompt
    prompt = "Create SO for ABC Industries for 100 pieces of Product-001 at Rs 500 each"
    print(f"Test 2: Full API call\nInput: {prompt}\n")
    result = process_prompt(prompt)
    print("Output:")
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    test_parse_output()
    try:
        test_clarity()
    except Exception as e:
        print(f"\nAPI test skipped or failed: {e}")
        print("(Run: python check_ollama.py  then  ollama run llama2)")
