"""
llm_router.py  —  Universal Gemini Smart Router
================================================
Handles:
  - Round-robin API key rotation across a pool loaded from GEMINI_API_KEYS / GEMINI_API_KEY
  - **1-strike quota tracking per (model, key) pair** — the moment a key returns 429/quota
    on a model it is immediately sidelined for that model (no retries on the same key).
  - When ALL keys are exhausted on a model it drops to the next model tier instantly.
  - Sidelined keys get a 60-second cooldown window, after which they are re-eligible.
  - Tiered fallback order (override via GEMINI_MODEL_TIERS env var, comma-separated):
        Tier 1 (Primary)  : gemini-2.5-flash
        Tier 2 (Fallback) : gemini-2.5-flash-lite
        Tier 3 (Fallback) : gemini-1.5-flash-latest
        Tier 4 (Fallback) : gemini-1.5-pro-latest
        Tier 5 (Last)     : gemini-flash-latest

Public API (all callers work unchanged):
  await invoke_smart_llm(messages, model_name=..., temperature=..., max_output_tokens=..., **kwargs)
        invoke_smart_llm_sync(messages, model_name=..., temperature=..., max_output_tokens=..., **kwargs)

Key-pool state is module-level so it is shared across all calls in the same worker process.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from collections import defaultdict
from itertools import cycle
from threading import Lock
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# API key pool
# ---------------------------------------------------------------------------

_keys_raw = os.getenv("GEMINI_API_KEYS", "") or os.getenv("GEMINI_API_KEY", "")
api_keys: List[str] = [k.strip() for k in _keys_raw.split(",") if k.strip()]

if not api_keys:
    logger.warning("[llm_router] No GEMINI_API_KEYS or GEMINI_API_KEY found in environment.")

# Infinite round-robin iterator — shared across the module
key_pool = cycle(api_keys) if api_keys else None

# ---------------------------------------------------------------------------
# Model tier fallback chain
# ---------------------------------------------------------------------------

_tier_env = os.getenv(
    "GEMINI_MODEL_TIERS",
    "gemini-2.5-flash,gemini-2.5-flash-lite,gemini-1.5-flash-latest,gemini-1.5-pro-latest,gemini-flash-latest",
)
MODEL_TIERS: List[str] = [m.strip() for m in _tier_env.split(",") if m.strip()]

# ---------------------------------------------------------------------------
# Per-(model, key) quota state
#   _quota_sidelined[(model, key)] = unix timestamp when it was sidelined
# ---------------------------------------------------------------------------

_quota_sidelined: Dict[tuple[str, str], float] = {}
_quota_lock = Lock()
_COOLDOWN_SECONDS = 20  # keys become re-eligible after this window


def _is_sidelined(model: str, key: str) -> bool:
    with _quota_lock:
        ts = _quota_sidelined.get((model, key))
        if ts is None:
            return False
        if time.time() - ts >= _COOLDOWN_SECONDS:
            # Cooldown expired — re-admit this key
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


def _available_keys_for(model: str) -> List[str]:
    """Return all API keys that are NOT currently sidelined for `model`."""
    return [k for k in api_keys if not _is_sidelined(model, k)]


def _is_quota_error(exc: Exception) -> bool:
    """Return True for errors that mean 'try a different model/key', not hard failures."""
    s = str(exc).lower()
    # 429 / quota:            try next key on same model
    # 404 NOT_FOUND:          model name doesn't exist — try next model tier
    # 403 PERMISSION_DENIED:  API key banned/project blocked — try next key
    return any(tok in s for tok in (
        "429", "quota", "exhausted", "rate limit", "resource_exhausted",
        "not_found", "not found",
        "403", "permission_denied", "permission denied", "denied access",
    ))


# ---------------------------------------------------------------------------
# Helper: build the tier list starting from the requested model
# ---------------------------------------------------------------------------

def _build_model_queue(requested_model: str) -> List[str]:
    """
    Returns the ordered list of models to try.
    The requested model is tried first; then the remaining tiers in order
    (skipping any that equal the requested model to avoid duplicates).
    """
    queue = [requested_model]
    for tier in MODEL_TIERS:
        if tier != requested_model:
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
) -> Any:
    """
    Attempt one model against all its available keys.
    Returns the LLM response on success.
    Raises RuntimeError if all keys are exhausted/sidelined for this model.
    Raises any non-quota exception immediately (let caller decide).
    """
    from langchain_google_genai import ChatGoogleGenerativeAI

    candidates = _available_keys_for(model)
    if not candidates:
        raise RuntimeError(f"All keys exhausted/sidelined for model '{model}'")

    for key in candidates:
        try:
            llm = ChatGoogleGenerativeAI(
                model=model,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
                google_api_key=key,
                max_retries=0,  # <-- CRITICAL: Disable Langchain's built-in sleep/retry!
                **kwargs,
            )
            response = llm.invoke(messages)
            response = _normalise_response(response)
            logger.debug("[llm_router] ✅ %s succeeded with key ...%s", model, key[-6:])
            return response

        except Exception as exc:
            if _is_quota_error(exc):
                _sideline_key(model, key)
                # Immediately try the next key — no sleep, stay fast
                continue
            # Non-quota error — propagate immediately
            raise

    # Reached here means every candidate key failed with quota
    raise RuntimeError(f"All keys exhausted/sidelined for model '{model}'")


async def _try_model_async(
    model: str,
    messages,
    temperature: float,
    max_output_tokens: int,
    kwargs: dict,
) -> Any:
    """Async version of _try_model_sync."""
    from langchain_google_genai import ChatGoogleGenerativeAI

    candidates = _available_keys_for(model)
    if not candidates:
        raise RuntimeError(f"All keys exhausted/sidelined for model '{model}'")

    for key in candidates:
        try:
            llm = ChatGoogleGenerativeAI(
                model=model,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
                google_api_key=key,
                max_retries=0,  # <-- CRITICAL: Disable Langchain's built-in sleep/retry!
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
    """Flatten list-content responses that Gemini sometimes returns."""
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
    model_name: str = "gemini-2.5-flash",
    temperature: float = 0.1,
    max_output_tokens: int = 800,
    **kwargs,
) -> Any:
    """
    Async smart LLM call with automatic key rotation and model-tier fallback.

    Strategy (fast):
      - 1 quota error on a key → sideline that key, try next key immediately.
      - All keys dead on the requested model → switch to next model tier instantly.
      - Sidelined keys recover after 20 s.
    """
    model_queue = _build_model_queue(model_name)

    for idx, current_model in enumerate(model_queue):
        if idx > 0:
            logger.warning(
                "[llm_router] 🔁 Switching model: '%s' exhausted all keys → trying '%s'",
                model_queue[idx - 1], current_model,
            )
        try:
            return await _try_model_async(current_model, messages, temperature, max_output_tokens, kwargs)
        except RuntimeError:
            # All keys exhausted for this model — move to next tier
            continue
        # Non-quota exceptions bubble up immediately

    raise Exception(
        f"[llm_router] 🚨 Critical: All models exhausted ({', '.join(model_queue)}). "
        "All API keys are on cooldown."
    )


def invoke_smart_llm_sync(
    messages,
    model_name: str = "gemini-2.5-flash",
    temperature: float = 0.1,
    max_output_tokens: int = 800,
    **kwargs,
) -> Any:
    """
    Sync smart LLM call with automatic key rotation and model-tier fallback.
    Same strategy as invoke_smart_llm — fast 1-strike key rotation.
    """
    model_queue = _build_model_queue(model_name)

    for idx, current_model in enumerate(model_queue):
        if idx > 0:
            logger.warning(
                "[llm_router] 🔁 Switching model: '%s' exhausted all keys → trying '%s'",
                model_queue[idx - 1], current_model,
            )
        try:
            return _try_model_sync(current_model, messages, temperature, max_output_tokens, kwargs)
        except RuntimeError:
            continue

    raise Exception(
        f"[llm_router] 🚨 Critical: All models exhausted ({', '.join(model_queue)}). "
        "All API keys are on cooldown."
    )
