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
