"""
Smoke test for shared LLM imports — run after any L0 LLM dependency change.

Usage:
    python -m shared.smoke_llm
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_SHARED = Path(__file__).resolve().parent
for _p in (_ROOT, _SHARED):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))


def main() -> int:
    errors: list[str] = []

    try:
        import langchain_openai  # noqa: F401
    except ImportError as exc:
        errors.append(f"langchain_openai: {exc}")

    try:
        import openai  # noqa: F401
    except ImportError as exc:
        errors.append(f"openai: {exc}")

    try:
        import langsmith  # noqa: F401
    except ImportError as exc:
        errors.append(f"langsmith: {exc}")

    try:
        from shared.llm_tracing import configure_llm_tracing, is_tracing_enabled, trace_llm
        configure_llm_tracing()
        assert callable(trace_llm)
        _ = is_tracing_enabled()
    except ImportError as exc:
        errors.append(f"shared.llm_tracing: {exc}")

    try:
        from langchain_openai import ChatOpenAI
        # Ensure httpx proxy kwarg mismatch does not break construction
        ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
            max_tokens=16,
            openai_api_key="sk-test",
            max_retries=0,
        )
    except TypeError as exc:
        if "proxies" in str(exc):
            errors.append(f"ChatOpenAI proxies kwarg mismatch: {exc}")
        # Other TypeErrors from dummy key are acceptable
    except Exception:
        pass  # missing/invalid key is fine for import smoke

    try:
        from openai import AsyncOpenAI
        # OS Clarity agentic loop uses AsyncOpenAI directly (same httpx stack)
        AsyncOpenAI(api_key="sk-test")
    except TypeError as exc:
        if "proxies" in str(exc):
            errors.append(f"AsyncOpenAI proxies kwarg mismatch: {exc}")
    except Exception:
        pass

    try:
        from shared_llm import generate_json  # noqa: F401
    except ImportError as exc:
        errors.append(f"shared_llm: {exc}")

    try:
        from llm_router import invoke_smart_llm_sync  # noqa: F401
    except ImportError as exc:
        errors.append(f"llm_router: {exc}")

    if errors:
        print("LLM smoke FAILED:")
        for err in errors:
            print(f"  - {err}")
        return 1

    print("LLM smoke OK — shared imports and ChatOpenAI construction")
    return 0


if __name__ == "__main__":
    sys.exit(main())
