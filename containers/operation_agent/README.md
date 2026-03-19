# Operation Agent

Natural language → Create Sales Order in ERPNext. Uses **Ollama** for local LLM (no API key).

## Setup

1. **Install Ollama** from [ollama.ai](https://ollama.ai), then:
   ```bash
   ollama pull llama2
   ollama run llama2     # keep running, or start before tests
   ```

2. **Python setup:**
   ```bash
   cd operation_agent
   pip install -r requirements.txt
   cp .env.example .env
   ```

## Run

```bash
uvicorn main:app --reload --port 8001
```

Open **http://localhost:8001** in your browser. Use port 8001 to avoid conflict with ERPNext (typically on 8000).

## Demo Mode (default)

No ERPNext needed. The agent simulates Sales Order creation. Set `DEMO_MODE=false` in `.env` and add ERPNext URL + API credentials to use real ERP.

## Test Clarity Agent

```bash
python test_clarity.py
```

## Project Structure

```
operation_agent/
├── main.py              # FastAPI app
├── config.py            # Config loader
├── agents/
│   ├── clarity_agent.py
│   ├── context_retrieval.py
│   ├── command_planning.py
│   ├── payload_generator.py
│   ├── validation_agent.py
│   ├── execution_agent.py
│   ├── result_formatter.py
│   └── orchestrator.py
├── knowledge/
│   ├── intent_definitions.json
│   ├── erpnext_field_mappings.json
│   ├── command_patterns.json
│   └── erpnext_doctype_graph.json
└── requirements.txt
```
