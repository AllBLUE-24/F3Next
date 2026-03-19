"""Storage abstraction — Minio or local filesystem (no Docker required)."""
import os
from pathlib import Path
from typing import BinaryIO

# Use local storage when USE_LOCAL_STORAGE=true (default: no Docker needed)
USE_LOCAL_STORAGE = os.getenv("USE_LOCAL_STORAGE", "true").lower() in ("true", "1", "yes")
# Default: uploads/ in project root (parent of backend/)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
LOCAL_STORAGE_DIR = Path(os.getenv("LOCAL_STORAGE_DIR", str(_PROJECT_ROOT / "uploads"))).resolve()


def _ensure_local_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def store_file_local(object_name: str, data: BinaryIO, content_type: str = "application/octet-stream") -> str:
    """Store file on local disk. Returns path relative to storage root."""
    full_path = LOCAL_STORAGE_DIR / object_name
    _ensure_local_dir(full_path.parent)
    full_path.write_bytes(data.read())
    return object_name


def get_storage_backend() -> str:
    """Returns 'local' or 'minio'."""
    if USE_LOCAL_STORAGE:
        return "local"
    return "minio"
