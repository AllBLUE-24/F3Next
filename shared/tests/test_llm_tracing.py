"""Unit tests for shared/llm_tracing.py."""

from __future__ import annotations

import importlib
import os


def test_configure_llm_tracing_normalizes_langsmith_env(monkeypatch):
    monkeypatch.delenv("LANGCHAIN_TRACING_V2", raising=False)
    monkeypatch.delenv("LANGCHAIN_API_KEY", raising=False)
    monkeypatch.delenv("LANGCHAIN_PROJECT", raising=False)
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    monkeypatch.setenv("LANGSMITH_API_KEY", "ls-test-key")
    monkeypatch.setenv("LANGSMITH_PROJECT", "test-project")

    import shared.llm_tracing as tracing

    importlib.reload(tracing)

    assert os.environ["LANGCHAIN_TRACING_V2"] == "true"
    assert os.environ["LANGCHAIN_API_KEY"] == "ls-test-key"
    assert os.environ["LANGCHAIN_PROJECT"] == "test-project"
    assert tracing.is_tracing_enabled() is True


def test_trace_llm_decorator_preserves_callable():
    from shared.llm_tracing import trace_llm

    @trace_llm(name="smoke_fn", run_type="llm")
    def _fn(x: int) -> int:
        return x + 1

    assert _fn(1) == 2
