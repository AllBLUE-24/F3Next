"""
llm_router.py  —  Universal Smart Router (OpenAI & Gemini)
================================================
Handles:
  - Round-robin API key rotation across a pool loaded from GEMINI_API_KEYS and OPENAI_API_KEYS
  - **1-strike quota tracking per (model, key) pair** — the moment a key returns 429/quota
    on a model it is immediately sidelined for that model (no retries on the same key).
  - When ALL keys are exhausted on a model it drops to the next model tier instantly.
  - Sidelined keys get a 60-second cooldown window, after which they are re-eligible.
  - Tiered fallback order (override via OPENAI_MODEL_TIERS or GEMINI_MODEL_TIERS).

Public API (all callers work unchanged):
  await invoke_smart_llm(messages, model_name=..., temperature=..., max_output_tokens=..., **kwargs)
        invoke_smart_llm_sync(messages, model_name=..., temperature=..., max_output_tokens=..., **kwargs)
  await invoke_agentic_loop(prompt, tool_dispatcher, schema, allowed_entity_types, max_tokens, model_name)
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from collections import defaultdict
from itertools import cycle
from threading import Lock
from typing import Any, Dict, List, Optional, Type
from pydantic import BaseModel

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# API key pool
# ---------------------------------------------------------------------------

_gemini_keys_raw = os.getenv("GEMINI_API_KEYS", "") or os.getenv("GEMINI_API_KEY", "")
gemini_api_keys: List[str] = [k.strip() for k in _gemini_keys_raw.split(",") if k.strip()]

_gemini_keys_raw_complex = os.getenv("GEMINI_API_KEYS_COMPLEX", "")
gemini_complex_api_keys: List[str] = [k.strip() for k in _gemini_keys_raw_complex.split(",") if k.strip()]

_openai_keys_raw = os.getenv("OPENAI_API_KEYS", "") or os.getenv("OPENAI_API_KEY", "")
openai_api_keys: List[str] = [k.strip() for k in _openai_keys_raw.split(",") if k.strip()]

_openai_keys_raw_complex = os.getenv("OPENAI_API_KEYS_COMPLEX", "")
openai_complex_api_keys: List[str] = [k.strip() for k in _openai_keys_raw_complex.split(",") if k.strip()]

if not gemini_api_keys and not openai_api_keys:
    logger.warning("[llm_router] No API keys found in environment for Gemini or OpenAI.")

# ---------------------------------------------------------------------------
# Model tier fallback chain
# ---------------------------------------------------------------------------

_gemini_tier_env = os.getenv(
    "GEMINI_MODEL_TIERS",
    "gemini-2.5-flash,gemini-2.5-flash-lite,gemini-1.5-flash-latest,gemini-1.5-pro-latest,gemini-flash-latest",
)
GEMINI_MODEL_TIERS: List[str] = [m.strip() for m in _gemini_tier_env.split(",") if m.strip()]

_openai_tier_env = os.getenv(
    "OPENAI_MODEL_TIERS",
    "gpt-4o-mini,gpt-4o,gpt-4-turbo",
)
OPENAI_MODEL_TIERS: List[str] = [m.strip() for m in _openai_tier_env.split(",") if m.strip()]

# ---------------------------------------------------------------------------
# Per-(model, key) quota state
# ---------------------------------------------------------------------------

_quota_sidelined: Dict[tuple[str, str], float] = {}
_quota_lock = Lock()
_COOLDOWN_SECONDS = 20


def _is_openai(model: str) -> bool:
    return model.startswith("gpt-") or model.startswith("o1-") or model.startswith("o3-")


def _is_sidelined(model: str, key: str) -> bool:
    with _quota_lock:
        ts = _quota_sidelined.get((model, key))
        if ts is None:
            return False
        if time.time() - ts >= _COOLDOWN_SECONDS:
            del _quota_sidelined[(model, key)]
            logger.debug("[llm_router] Key ...%s re-admitted for %s after cooldown", key[-6:], model)
            return False
        return True


def _sideline_key(model: str, key: str) -> None:
    with _quota_lock:
        _quota_sidelined[(model, key)] = time.time()
    logger.warning(
        "[llm_router] 🔴 Key ...%s sidelined for model '%s' (quota/429). "
        "Will retry after %ds.",
        key[-6:], model, _COOLDOWN_SECONDS,
    )


def _select_key_list(task_type: str, model: str) -> List[str]:
    is_openai = _is_openai(model)
    is_complex = str(task_type).lower().strip() == "complex"
    
    if is_openai:
        if is_complex and openai_complex_api_keys:
            return openai_complex_api_keys
        return openai_api_keys
    else:
        if is_complex and gemini_complex_api_keys:
            return gemini_complex_api_keys
        return gemini_api_keys


def _available_keys_for(model: str, keys: List[str]) -> List[str]:
    return [k for k in keys if not _is_sidelined(model, k)]


def _is_quota_error(exc: Exception) -> bool:
    s = str(exc).lower()
    return any(tok in s for tok in (
        "429", "quota", "exhausted", "rate limit", "resource_exhausted",
        "not_found", "not found",
        "403", "401", "permission_denied", "permission denied", "denied access", "unauthorized",
    ))


def _build_model_queue(requested_model: str) -> List[str]:
    tiers = OPENAI_MODEL_TIERS if _is_openai(requested_model) else GEMINI_MODEL_TIERS
    queue = [requested_model]
    for tier in tiers:
        if tier != requested_model:
            queue.append(tier)
            
    # Cross-provider fallback
    if _is_openai(requested_model) and gemini_api_keys:
        for tier in GEMINI_MODEL_TIERS:
            if tier not in queue:
                queue.append(tier)
    elif not _is_openai(requested_model) and openai_api_keys:
        for tier in OPENAI_MODEL_TIERS:
            if tier not in queue:
                queue.append(tier)
                
    return queue

# ---------------------------------------------------------------------------
# Core routing logic — sync
# ---------------------------------------------------------------------------

def _try_model_sync(
    model: str,
    messages,
    temperature: float,
    max_output_tokens: int,
    kwargs: dict,
    keys: List[str],
) -> Any:
    candidates = _available_keys_for(model, keys)
    if not candidates:
        raise RuntimeError(f"All keys exhausted/sidelined for model '{model}'")

    for key in candidates:
        try:
            if _is_openai(model):
                from langchain_openai import ChatOpenAI
                llm = ChatOpenAI(
                    model=model,
                    temperature=temperature,
                    max_tokens=max_output_tokens,
                    openai_api_key=key,
                    max_retries=0,
                    **kwargs,
                )
            else:
                from langchain_google_genai import ChatGoogleGenerativeAI
                llm = ChatGoogleGenerativeAI(
                    model=model,
                    temperature=temperature,
                    max_output_tokens=max_output_tokens,
                    google_api_key=key,
                    max_retries=0,
                    **kwargs,
                )
                
            response = llm.invoke(messages)
            response = _normalise_response(response)
            logger.debug("[llm_router] ✅ %s succeeded with key ...%s", model, key[-6:])
            return response

        except Exception as exc:
            if _is_quota_error(exc):
                _sideline_key(model, key)
                continue
            raise

    raise RuntimeError(f"All keys exhausted/sidelined for model '{model}'")


async def _try_model_async(
    model: str,
    messages,
    temperature: float,
    max_output_tokens: int,
    kwargs: dict,
    keys: List[str],
) -> Any:
    candidates = _available_keys_for(model, keys)
    if not candidates:
        raise RuntimeError(f"All keys exhausted/sidelined for model '{model}'")

    for key in candidates:
        try:
            if _is_openai(model):
                from langchain_openai import ChatOpenAI
                llm = ChatOpenAI(
                    model=model,
                    temperature=temperature,
                    max_tokens=max_output_tokens,
                    openai_api_key=key,
                    max_retries=0,
                    **kwargs,
                )
            else:
                from langchain_google_genai import ChatGoogleGenerativeAI
                llm = ChatGoogleGenerativeAI(
                    model=model,
                    temperature=temperature,
                    max_output_tokens=max_output_tokens,
                    google_api_key=key,
                    max_retries=0,
                    **kwargs,
                )
                
            response = await llm.ainvoke(messages)
            response = _normalise_response(response)
            logger.debug("[llm_router] ✅ %s succeeded with key ...%s", model, key[-6:])
            return response

        except Exception as exc:
            if _is_quota_error(exc):
                _sideline_key(model, key)
                continue
            raise

    raise RuntimeError(f"All keys exhausted/sidelined for model '{model}'")


# ---------------------------------------------------------------------------
# Response normalisation
# ---------------------------------------------------------------------------

def _normalise_response(response: Any) -> Any:
    if isinstance(getattr(response, "content", None), list):
        content_str = " ".join(
            p.get("text", "") for p in response.content
            if isinstance(p, dict) and "text" in p
        )
        try:
            response.content = content_str
        except Exception:
            class _Simple:
                def __init__(self, c):
                    self.content = c
            return _Simple(content_str)
    return response


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def invoke_smart_llm(
    messages,
    model_name: str = "gpt-4o-mini",
    temperature: float = 0.1,
    max_output_tokens: int = 800,
    task_type: str = "simple",
    **kwargs,
) -> Any:
    model_queue = _build_model_queue(model_name)

    for idx, current_model in enumerate(model_queue):
        keys = _select_key_list(task_type, current_model)
        if idx > 0:
            logger.warning(
                "[llm_router] 🔁 Switching model: '%s' exhausted all keys → trying '%s'",
                model_queue[idx - 1], current_model,
            )
        try:
            return await _try_model_async(current_model, messages, temperature, max_output_tokens, kwargs, keys)
        except RuntimeError:
            continue

    raise Exception(
        f"[llm_router] 🚨 Critical: All models exhausted ({', '.join(model_queue)}). "
        "All API keys are on cooldown."
    )


def invoke_smart_llm_sync(
    messages,
    model_name: str = "gpt-4o-mini",
    temperature: float = 0.1,
    max_output_tokens: int = 800,
    task_type: str = "simple",
    **kwargs,
) -> Any:
    model_queue = _build_model_queue(model_name)

    for idx, current_model in enumerate(model_queue):
        keys = _select_key_list(task_type, current_model)
        if idx > 0:
            logger.warning(
                "[llm_router] 🔁 Switching model: '%s' exhausted all keys → trying '%s'",
                model_queue[idx - 1], current_model,
            )
        try:
            return _try_model_sync(current_model, messages, temperature, max_output_tokens, kwargs, keys)
        except RuntimeError:
            continue

    raise Exception(
        f"[llm_router] 🚨 Critical: All models exhausted ({', '.join(model_queue)}). "
        "All API keys are on cooldown."
    )


async def invoke_agentic_loop(
    prompt: str,
    tool_dispatcher: dict,
    schema: Type[BaseModel],
    allowed_entity_types: Optional[List[str]] = None,
    max_tokens: int = 1200,
    model_name: str = "gpt-4o-mini",
) -> dict:
    model_queue = _build_model_queue(model_name)

    for idx, current_model in enumerate(model_queue):
        keys = _select_key_list("simple", current_model)
        
        if _is_openai(current_model):
            from shared.llm_providers.openai_provider import OpenAIProvider
            provider = OpenAIProvider(keys)
        else:
            from shared.llm_providers.gemini_provider import GeminiProvider
            provider = GeminiProvider(keys)

        try:
            return await provider.invoke_agentic_loop(
                prompt=prompt,
                tool_dispatcher=tool_dispatcher,
                schema=schema,
                allowed_entity_types=allowed_entity_types,
                max_tokens=max_tokens,
                model_name=current_model,
            )
        except RuntimeError:
            continue
            
    raise Exception(
        f"[llm_router] 🚨 Critical: All models exhausted ({', '.join(model_queue)}). "
        "All API keys are on cooldown for agentic loop."
    )
