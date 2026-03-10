"""Check Ollama connection and list available models."""
import httpx

from config import OLLAMA_BASE_URL, OLLAMA_MODEL


def check_ollama():
    """Verify Ollama is running and list models."""
    base = OLLAMA_BASE_URL.rstrip("/")
    print(f"Ollama base URL: {base}")
    print(f"Configured model: {OLLAMA_MODEL}\n")

    # Check if Ollama is running
    try:
        r = httpx.get(f"{base.replace('/v1', '')}/api/tags", timeout=5)
        r.raise_for_status()
        data = r.json()
        models = data.get("models", [])
        names = [m.get("name", "") for m in models]
        print("Available models:", names or "(none)")
        if names and OLLAMA_MODEL not in names:
            # Check if it's a tag match (e.g. llama3.2:3b)
            matches = [n for n in names if n.startswith(OLLAMA_MODEL.split(":")[0])]
            if matches:
                print(f"\nTip: Use OLLAMA_MODEL={matches[0]} in .env")
            else:
                print(f"\nTip: Run 'ollama pull {OLLAMA_MODEL}' or use OLLAMA_MODEL={names[0]}")
    except httpx.ConnectError:
        print("ERROR: Cannot connect to Ollama. Is it running?")
        print("  Run: ollama serve  (or just: ollama run llama2)")
        return False
    except Exception as e:
        print(f"ERROR: {e}")
        return False

    print("\nOllama is ready.")
    return True


if __name__ == "__main__":
    check_ollama()
