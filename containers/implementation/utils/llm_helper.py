"""
containers/implementation/utils/llm_helper.py
=============================================
Backward-compatible shim.

All implementation agents import `generate_json` from here — that import
continues to work unchanged. The actual logic now lives in the root
`shared_llm.py` so every container (os/, discovery/, implementation/) can
use the same universal helper.

Existing call sites require zero modification:
    from containers.implementation.utils.llm_helper import generate_json
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is on the path (needed when running as a sub-container)
_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# Re-export everything from the universal helper
from shared_llm import generate_json  # noqa: F401, E402

__all__ = ["generate_json"]
