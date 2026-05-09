import asyncio
import json
import logging
from typing import Any, List, Optional, Type
import re
from pydantic import BaseModel

from shared.llm_providers.base import AgenticProvider

logger = logging.getLogger(__name__)

class GeminiProvider(AgenticProvider):
    def __init__(self, api_keys: List[str]):
        self.api_keys = api_keys

    async def invoke_structured_output(
        self,
        prompt: str,
        schema: Type[BaseModel],
        system_instruction: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: int = 2000,
        model_name: str = "gemini-2.5-flash",
    ) -> dict:
        from google import genai
        from google.genai import types as gt
        from llm_router import _is_sidelined

        available_keys = [k for k in self.api_keys if not _is_sidelined(model_name, k)]
        if not available_keys:
            available_keys = self.api_keys
        if not available_keys:
            raise ValueError("No Gemini API keys available")

        contents = [gt.Content(role="user", parts=[gt.Part(text=prompt)])]
        cfg = gt.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=temperature,
            max_output_tokens=max_tokens,
            response_mime_type="application/json",
            response_schema=schema,
        )

        last_err = None
        for attempt in range(2):
            for key in available_keys:
                client = genai.Client(api_key=key)
                try:
                    resp = await client.aio.models.generate_content(
                        model=model_name,
                        contents=contents,
                        config=cfg,
                    )
                    if getattr(resp, "parsed", None):
                        return resp.parsed.model_dump(mode="json")
                    raise ValueError("Gemini structured output returned no parsed schema")
                except Exception as e:
                    err_str = str(e)
                    if any(tok in err_str.lower() for tok in (
                        "429", "quota", "exhausted",
                        "not_found", "not found",
                        "403", "permission_denied", "permission denied", "denied access",
                    )):
                        logger.warning(f"[GeminiProvider] Key/model rotated ({err_str[:100]})")
                        last_err = e
                        continue
                    raise ValueError(f"Generation failed: {e}")
                finally:
                    if hasattr(client.aio, "aclose"):
                        try:
                            await client.aio.aclose()
                        except Exception:
                            pass
            if attempt == 0:
                logger.warning("[GeminiProvider] All keys exhausted! Sleeping 10s...")
                await asyncio.sleep(10)
        raise ValueError(f"All keys exhausted or failed. Last error: {last_err}")

    async def invoke_agentic_loop(
        self,
        prompt: str,
        tool_dispatcher: dict,
        schema: Type[BaseModel],
        allowed_entity_types: Optional[List[str]] = None,
        max_tokens: int = 1200,
        model_name: str = "gemini-2.5-flash",
    ) -> dict:
        from google import genai
        from google.genai import types as gt
        from llm_router import _is_sidelined

        available_keys = [k for k in self.api_keys if not _is_sidelined(model_name, k)]
        if not available_keys:
            available_keys = self.api_keys
        if not available_keys:
            raise ValueError("No Gemini API keys available")

        async def _generate_with_retry(contents, config):
            last_err = None
            for attempt in range(2):
                for key in available_keys:
                    client = genai.Client(api_key=key)
                    try:
                        resp = await client.aio.models.generate_content(
                            model=model_name, contents=contents, config=config,
                        )
                        return resp
                    except Exception as e:
                        err_str = str(e)
                        if any(tok in err_str.lower() for tok in (
                            "429", "quota", "exhausted",
                            "not_found", "not found",
                            "403", "permission_denied", "permission denied", "denied access",
                        )):
                            logger.warning(f"[GeminiProvider] Key/model rotated ({err_str[:100]})")
                            last_err = e
                            continue
                        raise ValueError(f"Generation failed: {e}")
                    finally:
                        if hasattr(client.aio, "aclose"):
                            try:
                                await client.aio.aclose()
                            except Exception:
                                pass
                if attempt == 0:
                    logger.warning("[GeminiProvider] All keys exhausted! Sleeping 10s...")
                    await asyncio.sleep(10)
            raise ValueError(f"All keys exhausted or failed. Last error: {last_err}")

        has_tools = bool(tool_dispatcher)
        genai_tools = None
        if has_tools:
            props: dict[str, Any] = {
                "query": {"type": "string"},
                "entity_type": {"type": "string"},
            }
            if allowed_entity_types:
                props["entity_type"]["enum"] = allowed_entity_types

            genai_tools = [gt.Tool(function_declarations=[
                gt.FunctionDeclaration(
                    name="search_cvs_master_data",
                    description=(
                        "Search ERP master data (from CVS) for the requested entity type. "
                        "Returns up to 10 records. Each Item includes: item_code, "
                        "item_name, stock_uom, weight_per_unit, weight_uom. "
                        "Retry with a shorter keyword if 0 results are returned."
                    ),
                    parameters={
                        "type": "object",
                        "properties": props,
                        "required": ["query"],
                    },
                )
            ])]

        contents = [gt.Content(role="user", parts=[gt.Part(text=prompt)])]
        collected_results: list[dict] = []

        tool_cfg = gt.GenerateContentConfig(
            system_instruction=(
                "You are the F3Next Clarity Agent. Search ERP master data using "
                "search_cvs_master_data before forming any intent. "
                "Retry with shorter keywords if 0 results. "
                "Never guess an item_code or customer name."
            ),
            tools=genai_tools,
            temperature=0.1,
            max_output_tokens=max_tokens,
        )

        for _iter in range(3):
            try:
                resp = await _generate_with_retry(contents=contents, config=tool_cfg)
            except Exception as e:
                raise ValueError(f"Phase 1 generate_content failed (iter {_iter}): {e}")

            candidate = resp.candidates[0] if resp.candidates else None
            if not candidate:
                raise ValueError("No candidates in Phase 1 response")

            fn_calls = [
                p.function_call
                for p in candidate.content.parts
                if p.function_call is not None
            ]

            if not fn_calls or not has_tools:
                break

            contents.append(candidate.content)
            response_parts = []
            for fc in fn_calls:
                fn_name = fc.name
                fn_args = dict(fc.args)
                logger.info("[GeminiProvider] Tool call: %s(%s)", fn_name, fn_args)

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
                    "[GeminiProvider] Tool '%s' returned %d result(s)",
                    fn_name, len(fn_result) if isinstance(fn_result, list) else 1,
                )
                collected_results.append({
                    "tool": fn_name, "query": fn_args, "results": fn_result,
                })
                response_parts.append(gt.Part(
                    function_response=gt.FunctionResponse(
                        name=fn_name, response={"result": fn_result},
                    )
                ))

            contents.append(gt.Content(role="tool", parts=response_parts))

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
            ext_resp = await _generate_with_retry(
                contents=[gt.Content(role="user", parts=[gt.Part(text=extraction_prompt)])],
                config=gt.GenerateContentConfig(
                    system_instruction=extraction_sys,
                    temperature=0.1,
                    max_output_tokens=max_tokens,
                    response_mime_type="application/json",
                    response_schema=schema,
                ),
            )
        except Exception as e:
            raise ValueError(f"Phase 2 structured extraction failed: {e}")

        if getattr(ext_resp, "parsed", None):
            return ext_resp.parsed.model_dump()

        raw = ext_resp.text
        if not raw:
            raise ValueError("Phase 2 returned empty response and no parsed schema")

        cleaned = re.sub(r'^```(?:json)?\s*', '', raw, flags=re.MULTILINE)
        cleaned = re.sub(r'\s*```\s*$', '', cleaned, flags=re.MULTILINE).strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            sanitized = self._sanitize_json(cleaned)
            try:
                return json.loads(sanitized)
            except json.JSONDecodeError:
                pass
            repaired = self._repair_json(sanitized)
            if repaired:
                try:
                    return json.loads(repaired)
                except json.JSONDecodeError:
                    pass
            raise ValueError(f"Could not parse JSON from Phase 2 extraction: {cleaned[:200]}")

    def _sanitize_json(self, text: str) -> str:
        text = re.sub(r'("(?:[^"\\]|\\.)*")\s+(?=["{\[\-\d])', r'\1: ', text)
        text = re.sub(r',\s*([}\]])', r'\1', text)
        text = re.sub(r"(?<![\\])'", '"', text)
        text = re.sub(r'\bTrue\b', 'true', text)
        text = re.sub(r'\bFalse\b', 'false', text)
        text = re.sub(r'\bNone\b', 'null', text)
        return text

    def _repair_json(self, text: str) -> str | None:
        if not text.strip().startswith('{'):
            return None
        stack = []
        in_string = False
        escape = False
        for ch in text:
            if escape:
                escape = False
                continue
            if ch == '\\' and in_string:
                escape = True
                continue
            if ch == '"' and not escape:
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch in ('{', '['):
                stack.append('}' if ch == '{' else ']')
            elif ch in ('}', ']'):
                if stack and stack[-1] == ch:
                    stack.pop()
        if not stack:
            return None
        if in_string:
            text += '"'
        text = text.rstrip().rstrip(',')
        return text + ''.join(reversed(stack))
