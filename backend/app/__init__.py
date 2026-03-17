"""
Backend application package.

This repo uses a top-level `shared/` package that lives at the repository root.
When running backend modules from `backend/` (or importing `app.*` directly),
ensure the repository root is on `sys.path` so `import shared` works reliably.
"""

from __future__ import annotations

import sys
from pathlib import Path

# backend/app/__init__.py -> backend/app -> backend -> repo root
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.append(str(_REPO_ROOT))

