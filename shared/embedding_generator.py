from __future__ import annotations

import asyncio
import logging
import os
from itertools import cycle
from typing import Iterable, List, Optional

import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


_EMBEDDING_MODEL = os.getenv("GEMINI_EMBEDDING_MODEL", "models/gemini-embedding-001")
_EMBED_URL_TPL = (
    "https://generativelanguage.googleapis.com/v1beta/"
    f"{_EMBEDDING_MODEL}:embedContent?key={{key}}"
)

_keys_raw = os.getenv("GEMINI_API_KEYS", "") or os.getenv("GEMINI_API_KEY", "")
_api_keys: List[str] = [k.strip() for k in _keys_raw.split(",") if k.strip()]
_key_pool = cycle(_api_keys) if _api_keys else None

_EMBED_CONCURRENCY = int(os.getenv("EMBED_CONCURRENCY", "5") or "5")
_embed_sem = asyncio.Semaphore(_EMBED_CONCURRENCY)


def embedding_to_pgvector_str(values: Iterable[float]) -> str:
    vals = list(values)
    return "[" + ",".join(map(str, vals)) + "]"


async def generate_embedding(text: str, *, timeout_s: float = 20.0) -> list[float]:
    """
    Runtime embedding generation for RAG queries.
    Uses Gemini embedding endpoint with round-robin key rotation.
    """
    if not _api_keys or not _key_pool:
        raise RuntimeError("No GEMINI_API_KEYS configured for embedding generation.")

    payload = {"model": _EMBEDDING_MODEL, "content": {"parts": [{"text": text}]}}

    async with _embed_sem:
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            last_err: Optional[Exception] = None
            # Try each key once (fast), then fail.
            for _ in range(len(_api_keys)):
                key = next(_key_pool)
                try:
                    resp = await client.post(_EMBED_URL_TPL.format(key=key), json=payload)
                    data = resp.json()
                    if "error" in data:
                        msg = str(data["error"].get("message", "")).lower()
                        if any(tok in msg for tok in ("429", "quota", "exhausted", "rate")):
                            last_err = RuntimeError(f"Embedding quota hit for key ...{key[-6:]}")
                            continue
                        raise RuntimeError(f"Embedding API error: {data['error']}")
                    return data["embedding"]["values"]
                except Exception as e:
                    last_err = e
                    continue

            raise RuntimeError(f"All embedding keys failed. Last error: {last_err}")

