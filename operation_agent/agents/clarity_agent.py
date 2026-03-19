"""Clarity Agent: Parse user prompt → intent + entities."""
import json
from typing import Any

from config import OLLAMA_BASE_URL, OLLAMA_MODEL, KNOWLEDGE_DIR
from utils import parse_clarity_output


def load_intent_definitions() -> dict:
    """Load intent definitions from knowledge base."""
    path = KNOWLEDGE_DIR / "intent_definitions.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


SYSTEM_PROMPT = """You extract intent and entities from ERP commands. Output ONLY valid JSON, no markdown.

Example 1 - Input: "Create SO for ABC Industries for 100 pieces of Product-001 at Rs 500 each"
Output: {"intent": "create_sales_order", "entities": {"customer": "ABC Industries", "items": [{"item": "Product-001", "qty": 100, "rate": 500}]}, "confidence": 0.95}

Example 2 - Input: "Create sales order for Tech Solutions Ltd: 50 units of Laptop-X at 45000, 20 units of Mouse-Pro at 800"
Output: {"intent": "create_sales_order", "entities": {"customer": "Tech Solutions Ltd", "items": [{"item": "Laptop-X", "qty": 50, "rate": 45000}, {"item": "Mouse-Pro", "qty": 20, "rate": 800}]}, "confidence": 0.95}

Rules:
- Output valid JSON only. Use commas between array elements. No trailing commas.
- Extract ACTUAL customer name, item name, quantity, rate from the message
- ALWAYS include "rate" for each item when user mentions price (e.g. "at Rs 500", "at 500 each")
- Multiple items = separate objects in items array, each with item, qty, rate
- If rate not mentioned, use null
"""

USER_PROMPT_TEMPLATE = """Extract from this prompt. Return JSON with actual values:

"{prompt}"
"""


def process_prompt(prompt: str) -> dict[str, Any]:
    """
    Process user prompt and return structured intent + entities.

    Returns:
        {
            "intent": "create_sales_order",
            "entities": {"customer": "...", "items": [{"item": "...", "qty": 0, "rate": 0}]},
            "confidence": 0.92
        }
    """
    import httpx

    base = OLLAMA_BASE_URL.rstrip("/")
    if "/v1" not in base:
        base = f"{base}/v1"
    url = f"{base}/chat/completions"
    user_msg = USER_PROMPT_TEMPLATE.format(prompt=prompt)
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        "temperature": 0.1,
        "stream": False,
    }

    # Local LLM can take 2-3 min on first load; use 5 min timeout
    with httpx.Client(timeout=300) as client:
        r = client.post(url, json=payload)
        r.raise_for_status()
        data = r.json()

    # Handle OpenAI-compatible (choices) or Ollama native (message) response
    content = None
    if "choices" in data and data["choices"]:
        message = data["choices"][0].get("message", {})
        content = message.get("content") or message.get("text")
    if not content and "message" in data:
        content = data["message"].get("content")
    if not content and "response" in data:
        content = data.get("response", "")
    if not content:
        raise ValueError(f"Ollama returned empty content. Response: {data}")

    return parse_clarity_output(content)


if __name__ == "__main__":
    # Test
    test_prompt = "Create SO for ABC Industries for 100 pieces of Product-001 at ₹500 each"
    result = process_prompt(test_prompt)
    print(json.dumps(result, indent=2))
