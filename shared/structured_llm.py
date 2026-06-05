"""
shared/structured_llm.py

Provider-agnostic structured output helper.

This is a thin compatibility layer over `llm_router.invoke_structured_llm`,
so application code can request typed outputs without caring whether the
active backend is Gemini or OpenAI.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional, Type, TypeVar

from pydantic import BaseModel

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

# IS structured steps (corpus, synthesis, data readiness) default to OpenAI unless overridden.
_DEFAULT_STRUCTURED_MODEL = (
    os.getenv("STRUCTURED_LLM_MODEL")
    or os.getenv("IS_STRUCTURED_MODEL")
    or "gpt-4o-mini"
)


async def generate_typed(
    *,
    prompt: str,
    schema: Type[T],
    model_name: str = _DEFAULT_STRUCTURED_MODEL,
    temperature: float = 0.0,
    max_output_tokens: int = 2000,
    system_instruction: Optional[str] = None,
) -> dict[str, Any]:
    """
    Generate schema-locked JSON via the router's active provider.

    Returns dict = schema.model_dump(mode="json").
    Raises ValueError on failure.
    """
    from llm_router import invoke_structured_llm

    return await invoke_structured_llm(
        prompt=prompt,
        schema=schema,
        model_name=model_name,
        temperature=temperature,
        max_tokens=max_output_tokens,
        system_instruction=system_instruction,
    )

