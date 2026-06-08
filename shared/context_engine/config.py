"""Paths and tunables for the Context Engine."""

from __future__ import annotations

import os
from pathlib import Path

# Repo root: shared/context_engine -> shared -> F3Next
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
KB_ROOT = _REPO_ROOT / "containers" / "knowledge_base"
ERPNEXT_KB = KB_ROOT / "erpnext"
COMMON_KB = KB_ROOT / "common"
F3ICHE_DIR = COMMON_KB / "f3iches"

L1_MAX_SIZE = int(os.getenv("CONTEXT_ENGINE_L1_MAX", "500"))
L1_TTL_SEC = int(os.getenv("CONTEXT_ENGINE_L1_TTL", "600"))
L2_TTL_SEC = int(os.getenv("CONTEXT_ENGINE_L2_TTL", "1800"))
REDIS_URL = os.getenv("REDIS_URL", "").strip()
