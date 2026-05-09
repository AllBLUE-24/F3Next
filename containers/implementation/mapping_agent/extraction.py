"""
Schema-locked extraction (Step B) for Mapping Agent.

For unstructured text, we use provider-agnostic structured outputs with a doctype-specific
Pydantic schema generated from the ERPNext KB.
"""

from __future__ import annotations

from typing import Any, Dict, List

from pydantic import ValidationError

from containers.implementation.mapping_agent.schema_builder import (
    build_extraction_wrapper_model,
)
from shared.structured_llm import generate_typed


async def extract_unstructured_records(
    *,
    doctype: str,
    content: str,
    filename: str,
    model_name: Optional[str] = None,
) -> List[Dict[str, Any]]:
    wrapper = build_extraction_wrapper_model(doctype)

    snippet = (content or "")[:6000]
    prompt = (
        "You are an ERPNext data extraction engine.\n"
        "Task: extract records for the given ERPNext doctype.\n"
        "Rules:\n"
        "- Output MUST match the provided JSON schema exactly (no extra keys).\n"
        "- Dates MUST be ISO format YYYY-MM-DD.\n"
        "- Child tables MUST be arrays (e.g., items[]), and mandatory child fields must be present.\n"
        "- If a value is missing in the text and optional in schema, leave it null.\n"
        "- Do not hallucinate unknown parties/items; extract only what is present.\n\n"
        f"Doctype: {doctype}\n"
        f"Filename: {filename}\n"
        f"Text:\n{snippet}\n\n"
        "Return strictly the JSON object matching the schema."
    )

    # Try schema-locked extraction; if it fails, re-run once with a tighter hint.
    try:
        res = await generate_typed(
            prompt=prompt,
            schema=wrapper,
            model_name=model_name or "gpt-4o-mini",
            temperature=0.0,
            max_output_tokens=6000,
            system_instruction="Return only the JSON object. No markdown.",
        )
        return list(res.get("records") or [])
    except Exception as e:
        # Second attempt: encourage producing at least one record
        prompt2 = prompt + "\n\nIf the text contains at least one record, you MUST return records with length >= 1."
        res = await generate_typed(
            prompt=prompt2,
            schema=wrapper,
            model_name=model_name or "gpt-4o-mini",
            temperature=0.0,
            max_output_tokens=6000,
            system_instruction="Return only the JSON object. No markdown.",
        )
        return list(res.get("records") or [])


def validate_records_against_schema(doctype: str, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Local validation/normalization pass: parse via Pydantic and re-dump as JSON.
    This coerces numeric/date types deterministically.
    """
    wrapper = build_extraction_wrapper_model(doctype)
    try:
        obj = wrapper.model_validate({"records": records})
    except ValidationError as ve:
        # Raise to let caller decide to retry or default-inject more aggressively
        raise ve
    return list(obj.model_dump(mode="json").get("records") or [])

