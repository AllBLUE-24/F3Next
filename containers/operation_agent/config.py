"""Configuration loader for Operation Agent."""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")  # Load from project dir (works regardless of cwd)

KNOWLEDGE_DIR = BASE_DIR / "knowledge"
# Doctype graph: use parent ERPNext folder if not in knowledge
DOCTYPE_GRAPH_PATH = (
    KNOWLEDGE_DIR / "erpnext_doctype_graph.json"
    if (KNOWLEDGE_DIR / "erpnext_doctype_graph.json").exists()
    else BASE_DIR.parent / "erpnext_doctype_graph.json"
)

# LLM: Ollama (local) - base_url needs trailing slash per Ollama docs
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1/")
_raw_model = os.getenv("OLLAMA_MODEL", "llama2:latest")
# Auto-append :latest if no tag (llama2 -> llama2:latest)
OLLAMA_MODEL = _raw_model if ":" in _raw_model else f"{_raw_model}:latest"

# ERPNext
_raw_url = os.getenv("ERPNEXT_URL", "").strip().rstrip("/")
# Treat placeholder URLs as not configured
_placeholders = ("your-erpnext-instance", "your-erpnext-instance.com", "yourcompany.erpnext.com")
ERPNEXT_URL = "" if any(p in _raw_url.lower() for p in _placeholders) else _raw_url
ERPNEXT_API_KEY = os.getenv("ERPNEXT_API_KEY", "")
ERPNEXT_API_SECRET = os.getenv("ERPNEXT_API_SECRET", "")
ERPNEXT_COMPANY = os.getenv("ERPNEXT_COMPANY", "")

# Demo mode: simulate Sales Order creation without ERPNext (for testing with local LLM only)
DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() in ("true", "1", "yes")


def get_erpnext_auth() -> tuple[str, str]:
    """Return (api_key, api_secret) for ERPNext API auth."""
    return (ERPNEXT_API_KEY, ERPNEXT_API_SECRET)
