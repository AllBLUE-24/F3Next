"""Utility functions."""
import json
import re


def _repair_json(text: str) -> str:
    """Fix common LLM JSON errors: trailing commas, missing commas between items."""
    # Remove trailing commas before } or ]
    text = re.sub(r",\s*}", "}", text)
    text = re.sub(r",\s*]", "]", text)
    # Add missing comma between adjacent objects in array: }{ -> },{
    text = re.sub(r"\}\s*\{", "},{", text)
    return text


def parse_clarity_output(response: str) -> dict:
    """Parse LLM response into structured output. Handle markdown, extra text, malformed JSON."""
    if not response or not isinstance(response, str):
        raise ValueError("Empty or invalid response")
    text = response.strip()
    if not text:
        raise ValueError("Empty response after strip")

    # Remove markdown code blocks
    if "```" in text:
        match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if match:
            text = match.group(1).strip()

    # Extract JSON object if wrapped in extra text
    json_match = re.search(r"\{[\s\S]*\}", text)
    if json_match:
        text = json_match.group(0)

    # Try parse, then repair common LLM errors and retry
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        text = _repair_json(text)
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            raise ValueError(f"Could not parse LLM output as JSON: {e}") from e
