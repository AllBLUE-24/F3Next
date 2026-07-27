"""Environment flags for Step 4 map & validate."""
from __future__ import annotations

import os


def _env_truthy(name: str, default: str = "true") -> bool:
    return os.getenv(name, default).lower() in ("true", "1", "yes")


def require_readiness_gate() -> bool:
    """When true, offline assess fails if readiness_level is red."""
    return _env_truthy("MAP_VALIDATE_REQUIRE_READINESS", "false")


def block_import_on_fail() -> bool:
    """When true, import_ready is false unless validation_level != fail."""
    return _env_truthy("MAP_VALIDATE_BLOCK_ON_FAIL", "true")
