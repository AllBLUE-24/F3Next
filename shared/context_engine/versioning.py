"""Cache key helpers and stable hashes for context versions."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Optional


def layers_hash(layers: list[str]) -> str:
    h = hashlib.sha256("|".join(sorted(layers)).encode()).hexdigest()[:16]
    return h


def context_cache_key(
    project_id: str,
    f3iche_id: str,
    layers: list[str],
    version: Optional[int],
) -> str:
    v = "latest" if version is None else str(version)
    lh = layers_hash(layers)
    return f"ctx:v1:{project_id}:{f3iche_id}:{lh}:{v}"


def json_checksum(obj: Any) -> str:
    raw = json.dumps(obj, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def tier1_cache_key(checksum: str) -> str:
    return f"tier1:v1:{checksum}"


def tier2_cache_key(f3iche_id: str, version: Optional[int]) -> str:
    v = "latest" if version is None else str(version)
    return f"tier2:v1:{f3iche_id}:{v}"


def tier3_cache_key(query_hash: str, top_k: int) -> str:
    return f"tier3:v1:{query_hash}:{top_k}"
