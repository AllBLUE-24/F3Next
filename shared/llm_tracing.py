"""
shared/llm_tracing.py — Central LangSmith tracing for L0 LLM calls.

LangChain routes auto-trace when LANGCHAIN_TRACING_V2=true.
Native SDK paths (OpenAI/Gemini providers, embeddings) use @trace_llm.

Env (either naming convention works):
  LANGCHAIN_TRACING_V2=true  |  LANGSMITH_TRACING=true
  LANGCHAIN_API_KEY=...      |  LANGSMITH_API_KEY=...
  LANGCHAIN_PROJECT=f3next   |  LANGSMITH_PROJECT=f3next
"""

from __future__ import annotations

import logging
import os
from typing import Any, Callable, TypeVar

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])

_configured = False


def _truthy(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in ("1", "true", "yes", "on")


def is_tracing_enabled() -> bool:
    return _truthy("LANGCHAIN_TRACING_V2") or _truthy("LANGSMITH_TRACING")


def configure_llm_tracing() -> bool:
    """Normalize env vars and log tracing status. Idempotent."""
    global _configured
    if _configured:
        return is_tracing_enabled()

    _configured = True

    if _truthy("LANGSMITH_TRACING") and not os.getenv("LANGCHAIN_TRACING_V2"):
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
    if os.getenv("LANGSMITH_API_KEY") and not os.getenv("LANGCHAIN_API_KEY"):
        os.environ["LANGCHAIN_API_KEY"] = os.environ["LANGSMITH_API_KEY"]
    if os.getenv("LANGSMITH_PROJECT") and not os.getenv("LANGCHAIN_PROJECT"):
        os.environ["LANGCHAIN_PROJECT"] = os.environ["LANGSMITH_PROJECT"]

    os.environ.setdefault("LANGCHAIN_PROJECT", "f3next")

    if is_tracing_enabled():
        project = os.getenv("LANGCHAIN_PROJECT", "f3next")
        logger.info("[llm_tracing] LangSmith enabled (project=%s)", project)
    else:
        logger.debug(
            "[llm_tracing] LangSmith disabled — set LANGCHAIN_TRACING_V2=true to enable"
        )
    return is_tracing_enabled()


def trace_llm(
    name: str | None = None,
    *,
    run_type: str = "llm",
    **trace_kwargs: Any,
) -> Callable[[F], F]:
    """LangSmith @traceable when installed; no-op otherwise."""

    def decorator(fn: F) -> F:
        configure_llm_tracing()
        try:
            from langsmith import traceable

            kwargs: dict[str, Any] = {
                "name": name or fn.__qualname__,
                "run_type": run_type,
                **trace_kwargs,
            }
            return traceable(**kwargs)(fn)  # type: ignore[return-value]
        except ImportError:
            logger.debug("[llm_tracing] langsmith not installed — skipping trace for %s", fn.__qualname__)
            return fn

    return decorator


# Configure on import so LangChain auto-instrumentation picks up env early.
configure_llm_tracing()
