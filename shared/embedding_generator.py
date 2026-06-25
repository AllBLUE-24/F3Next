from __future__ import annotations

import asyncio
import logging
import os
from itertools import cycle
from typing import Iterable, List, Optional

import httpx
from dotenv import load_dotenv

load_dotenv()

from shared.llm_tracing import configure_llm_tracing, trace_llm  # noqa: E402

configure_llm_tracing()

logger = logging.getLogger(__name__)

# OpenAI embedding configuration
_OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-large")
# Matches the existing kb_embeddings vector(3072) column
_OPENAI_EMBED_DIMS = int(os.getenv("OPENAI_EMBED_DIMS", "3072"))
_OPENAI_URL = "https://api.openai.com/v1/embeddings"

_openai_keys_raw = os.getenv("OPENAI_API_KEYS", "") or os.getenv("OPENAI_API_KEY", "")
_openai_api_keys: List[str] = [k.strip() for k in _openai_keys_raw.split(",") if k.strip()]
_openai_key_pool = cycle(_openai_api_keys) if _openai_api_keys else None

_EMBED_CONCURRENCY = int(os.getenv("EMBED_CONCURRENCY", "5") or "5")
_embed_sem = asyncio.Semaphore(_EMBED_CONCURRENCY)

def embedding_to_pgvector_str(values: Iterable[float]) -> str:
    vals = list(values)
    return "[" + ",".join(map(str, vals)) + "]"

@trace_llm(name="generate_embedding", run_type="embedding")
async def generate_embedding(text: str, *, timeout_s: float = 20.0) -> List[float]:
    """Generate an embedding for the given text using OpenAI's embedding endpoint.

    Uses round-robin key rotation across OPENAI_API_KEYS.
    Output is shortened to _OPENAI_EMBED_DIMS dimensions (default 3072) so it
    remains compatible with the existing pgvector vector(3072) column.
    """
    if not _openai_api_keys or not _openai_key_pool:
        raise RuntimeError("No OPENAI_API_KEYS configured for embedding generation.")

    payload = {
        "model": _OPENAI_EMBEDDING_MODEL,
        "input": text,
        "dimensions": _OPENAI_EMBED_DIMS,
    }

    async with _embed_sem:
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            last_err: Optional[Exception] = None
            for _ in range(len(_openai_api_keys)):
                key = next(_openai_key_pool)
                try:
                    resp = await client.post(
                        _OPENAI_URL,
                        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                        json=payload,
                    )
                    data = resp.json()
                    if "error" in data:
                        msg = str(data["error"].get("message", "")).lower()
                        if any(tok in msg for tok in ("429", "quota", "exhausted", "rate")):
                            last_err = RuntimeError(f"Embedding quota hit for key ...{key[-6:]}")
                            continue
                        raise RuntimeError(f"Embedding API error: {data['error']}")
                    # Expected response format: {"data": [{"embedding": [...]}, ...]}
                    return data["data"][0]["embedding"]
                except Exception as e:
                    last_err = e
                    continue
            raise RuntimeError(f"All embedding keys failed. Last error: {last_err}")
