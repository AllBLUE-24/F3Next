import asyncio
import json
import logging
from typing import Any, List, Optional, Type
from pydantic import BaseModel

from shared.llm_providers.base import AgenticProvider

logger = logging.getLogger(__name__)

class OpenAIProvider(AgenticProvider):
    def __init__(self, api_keys: List[str]):
        self.api_keys = api_keys

    async def invoke_structured_output(
        self,
        prompt: str,
        schema: Type[BaseModel],
        system_instruction: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: int = 2000,
        model_name: str = "gpt-4o-mini",
    ) -> dict:
        from openai import AsyncOpenAI
        from llm_router import _is_sidelined
        from shared.llm_schema_utils import (
            build_structured_system_instruction,
            repair_pydantic_dict,
        )

        available_keys = [k for k in self.api_keys if not _is_sidelined(model_name, k)]
        if not available_keys:
            available_keys = self.api_keys
        if not available_keys:
            raise ValueError("No OpenAI API keys available")

        sys_content = system_instruction or build_structured_system_instruction(schema)
        messages = [
            {"role": "system", "content": sys_content},
            {"role": "user", "content": prompt},
        ]

        last_err = None
        for attempt in range(2):
            for key in available_keys:
                client = AsyncOpenAI(api_key=key)
                try:
                    resp = await client.chat.completions.create(
                        model=model_name,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        response_format={"type": "json_object"},
                    )
                    raw = resp.choices[0].message.content
                    if not raw:
                        raise ValueError("Empty response from OpenAI structured output")
                    data = repair_pydantic_dict(json.loads(raw), schema)
                    parsed = schema.model_validate(data)
                    return parsed.model_dump(mode="json")
                except Exception as e:
                    err_str = str(e)
                    if any(tok in err_str.lower() for tok in (
                        "429", "rate limit", "quota", "exhausted",
                        "404", "not found",
                        "403", "401", "permission denied", "unauthorized",
                    )):
                        logger.warning(f"[OpenAIProvider] Key/model rotated ({err_str[:100]})")
                        last_err = e
                        continue
                    last_err = e
                    raise ValueError(f"Generation failed: {e}")
                finally:
                    await client.close()
            if attempt == 0:
                logger.warning("[OpenAIProvider] All keys exhausted! Sleeping 10s...")
                await asyncio.sleep(10)
        raise ValueError(f"All keys exhausted or failed. Last error: {last_err}")

    async def invoke_agentic_loop(
        self,
        prompt: str,
        tool_dispatcher: dict,
        schema: Type[BaseModel],
        allowed_entity_types: Optional[List[str]] = None,
        max_tokens: int = 1200,
        model_name: str = "gpt-4o-mini",
    ) -> dict:
        from openai import AsyncOpenAI
        from llm_router import _is_sidelined

        available_keys = [k for k in self.api_keys if not _is_sidelined(model_name, k)]
        if not available_keys:
            available_keys = self.api_keys
        if not available_keys:
            raise ValueError("No OpenAI API keys available")

        async def _generate_with_retry(messages, tools=None, response_format=None, temp=0.1):
            last_err = None
            for attempt in range(2):
                for key in available_keys:
                    client = AsyncOpenAI(api_key=key)
                    try:
                        kwargs = {
                            "model": model_name,
                            "messages": messages,
                            "temperature": temp,
                            "max_tokens": max_tokens,
                        }
                        if tools:
                            kwargs["tools"] = tools
                        if response_format:
                            kwargs["response_format"] = response_format

                        resp = await client.chat.completions.create(**kwargs)
                        return resp
                    except Exception as e:
                        err_str = str(e)
                        if any(tok in err_str.lower() for tok in (
                            "429", "rate limit", "quota", "exhausted",
                            "404", "not found",
                            "403", "401", "permission denied", "unauthorized",
                        )):
                            logger.warning(f"[OpenAIProvider] Key/model rotated ({err_str[:100]})")
                            last_err = e
                            continue
                        raise ValueError(f"Generation failed: {e}")
                    finally:
                        await client.close()
                if attempt == 0:
                    logger.warning("[OpenAIProvider] All keys exhausted! Sleeping 10s...")
                    await asyncio.sleep(10)
            raise ValueError(f"All keys exhausted or failed. Last error: {last_err}")

        has_tools = bool(tool_dispatcher)
        openai_tools = None
        if has_tools:
            props: dict[str, Any] = {
                "query": {"type": "string"},
                "entity_type": {"type": "string"},
            }
            if allowed_entity_types:
                props["entity_type"]["enum"] = allowed_entity_types

            openai_tools = [{
                "type": "function",
                "function": {
                    "name": "search_cvs_master_data",
                    "description": (
                        "Search ERP master data (from CVS) for the requested entity type. "
                        "Returns up to 10 records. Each Item includes: item_code, "
                        "item_name, stock_uom, weight_per_unit, weight_uom. "
                        "Retry with a shorter keyword if 0 results are returned."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": props,
                        "required": ["query"],
                        "additionalProperties": False,
                    }
                }
            }]

        messages = [
            {
                "role": "system",
                "content": (
                    "You are the F3Next Clarity Agent. Search ERP master data using "
                    "search_cvs_master_data before forming any intent. "
                    "Retry with shorter keywords if 0 results. "
                    "Never guess an item_code or customer name."
                )
            },
            {"role": "user", "content": prompt}
        ]
        collected_results: list[dict] = []

        for _iter in range(3):
            try:
                resp = await _generate_with_retry(messages=messages, tools=openai_tools)
            except Exception as e:
                raise ValueError(f"Phase 1 tool loop failed (iter {_iter}): {e}")

            choice = resp.choices[0]
            msg = choice.message

            if not msg.tool_calls or not has_tools:
                break

            # Append the assistant's message with tool_calls
            messages.append(msg)

            for tc in msg.tool_calls:
                fn_name = tc.function.name
                try:
                    fn_args = json.loads(tc.function.arguments)
                except Exception:
                    fn_args = {}

                logger.info("[OpenAIProvider] Tool call: %s(%s)", fn_name, fn_args)

                dispatcher_fn = tool_dispatcher.get(fn_name)
                if dispatcher_fn:
                    try:
                        fn_result = await dispatcher_fn(**fn_args)
                    except Exception as e:
                        logger.error("Tool '%s' raised: %s", fn_name, e)
                        fn_result = {"error": str(e)}
                else:
                    fn_result = {"error": f"Tool '{fn_name}' not found"}

                logger.info(
                    "[OpenAIProvider] Tool '%s' returned %d result(s)",
                    fn_name, len(fn_result) if isinstance(fn_result, list) else 1,
                )
                collected_results.append({
                    "tool": fn_name, "query": fn_args, "results": fn_result,
                })

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps({"result": fn_result}, default=str)
                })

        if collected_results:
            lines = []
            for tr in collected_results:
                res = tr["results"]
                lines.append(f"Searched: {tr['query']}")
                if isinstance(res, list):
                    for r in res[:5]:
                        parts = []
                        for k in ['item_code', 'item_name', 'name', 'customer_name', 'supplier_name', 'stock_uom', 'weight_per_unit']:
                            if r.get(k) is not None:
                                parts.append(f"{k}={r.get(k)}")
                        if parts:
                            lines.append("  " + "  ".join(parts))
                        else:
                            lines.append(f"  {r}")
                else:
                    lines.append(f"  {res}")
            tool_context = "\n".join(lines)
        else:
            tool_context = "No master data was searched."

        extraction_prompt = (
            f"ERP SEARCH RESULTS:\n{tool_context}\n\n"
            f"ORIGINAL USER COMMAND: {prompt}\n\n"
            "RULES:\n"
            "- item_code MUST be the exact code from the search results. Never invent one.\n"
            "- customer or supplier MUST be the exact name (or customer_name/supplier_name) from the search results. Never invent one.\n"
            "- If the user said '40 kg' but stock_uom is 'Nos' and weight_per_unit is 0.5, "
            "set qty = 40 / 0.5 = 80.\n"
            "- Set confidence >= 0.95 when item_code confirmed by search.\n"
            "- Produce the structured intent JSON now."
        )

        extraction_sys = (
            "You are an ERP intent extraction engine. "
            "Given search results and a user command, produce the structured intent. "
            "Output ONLY the JSON object matching the required schema."
        )

        try:
            # We use strict Structured Outputs
            response_format = {
                "type": "json_schema",
                "json_schema": {
                    "name": "intent_schema",
                    "strict": True,
                    "schema": schema.model_json_schema()
                }
            }
            # pydantic schema might have additionalProperties issues with strict=True
            # Let's use standard json_object for safety, as the prompt is very clear
            response_format = {"type": "json_object"}
            
            ext_messages = [
                {"role": "system", "content": extraction_sys},
                {"role": "user", "content": extraction_prompt}
            ]
            
            ext_resp = await _generate_with_retry(
                messages=ext_messages,
                response_format=response_format
            )
        except Exception as e:
            raise ValueError(f"Phase 2 structured extraction failed: {e}")

        raw = ext_resp.choices[0].message.content
        if not raw:
            raise ValueError("Phase 2 returned empty response")

        try:
            return json.loads(raw)
        except Exception as e:
            raise ValueError(f"Could not parse JSON from Phase 2 extraction: {raw[:200]}")
