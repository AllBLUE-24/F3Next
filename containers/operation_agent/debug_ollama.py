"""Debug: Print raw Ollama API response to diagnose issues."""
import json
import httpx
from config import OLLAMA_BASE_URL, OLLAMA_MODEL

base = OLLAMA_BASE_URL.rstrip("/")
if "/v1" not in base:
    base = f"{base}/v1"
url = f"{base}/chat/completions"

print(f"URL: {url}")
print(f"Model: {OLLAMA_MODEL}\n")

r = httpx.post(url, json={
    "model": OLLAMA_MODEL,
    "messages": [{"role": "user", "content": "Reply with: hello"}],
    "stream": False,
}, timeout=60)

print(f"Status: {r.status_code}")
try:
    data = r.json()
    print(f"Response keys: {list(data.keys())}")
    print(f"\nFull response:\n{json.dumps(data, indent=2)[:2000]}")
except Exception as e:
    print(f"Body (raw): {r.text[:500]}")
    print(f"Parse error: {e}")
