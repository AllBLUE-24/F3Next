"""Step 5 import configuration."""
from __future__ import annotations

import os


def require_map_validate_gate() -> bool:
    return os.getenv("IMPORT_REQUIRE_MAP_VALIDATE", "true").lower() in ("1", "true", "yes")


def block_on_validation_fail() -> bool:
    return os.getenv("IMPORT_BLOCK_ON_VALIDATION_FAIL", "true").lower() in ("1", "true", "yes")
