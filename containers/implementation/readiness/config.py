"""Environment flags for Step 3 readiness."""
from __future__ import annotations

import os


def _env_truthy(name: str, default: str = "true") -> bool:
    return os.getenv(name, default).lower() in ("true", "1", "yes")


def require_discovery_context() -> bool:
    """Fail assess when Discovery scope (seed_doctypes) is missing."""
    return _env_truthy("READINESS_REQUIRE_DISCOVERY", "true")


def live_schema_primary() -> bool:
    """Prefer live ERP schema over graph/KB when deployment_details exist."""
    return _env_truthy("READINESS_LIVE_SCHEMA_PRIMARY", "true")
