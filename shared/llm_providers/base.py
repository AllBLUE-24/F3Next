from typing import Any, Dict, List, Optional, Type
from pydantic import BaseModel

class AgenticProvider:
    async def invoke_agentic_loop(
        self,
        prompt: str,
        tool_dispatcher: dict,
        schema: Type[BaseModel],
        allowed_entity_types: Optional[List[str]] = None,
        max_tokens: int = 1200,
        model_name: str = "gpt-4o-mini",
    ) -> dict:
        raise NotImplementedError

    async def invoke_structured_output(
        self,
        prompt: str,
        schema: Type[BaseModel],
        system_instruction: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: int = 2000,
        model_name: str = "gpt-4o-mini",
    ) -> dict:
        raise NotImplementedError
