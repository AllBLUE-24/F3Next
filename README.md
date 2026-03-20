# F3Next (Implem_agent branch)

This is the **Implementation Agent** branch.

AI-powered ERP discovery and implementation for manufacturers.  
**Repository:** [AllBLUE-24/F3Next](https://github.com/AllBLUE-24/F3Next) · **Branch:** [Implem_agent](https://github.com/AllBLUE-24/F3Next/tree/Implem_agent)

---

## Prerequisites

- **Python 3.10+** (add to PATH)
- **Node.js 18+** and npm
- **Temporal CLI** (for Discovery workflows): e.g. `winget install Temporal.TemporalCLI` on Windows
- **Ollama** (optional, for local LLM): [ollama.ai](https://ollama.ai) — or use mock fallback
- **PostgreSQL** (optional for full stack): Docker or local; or use SQLite for dev

---

## Features in this application

| Feature | Description |
|--------|--------------|
| **Discovery (consultant chatbot)** | Chat flow that asks about industry, manufacturing/trading style, turnover, current systems, and pain points. Recommends ERP (e.g. ERPNext), price plan, and F3iche. Uses Temporal workflow + optional Ollama/Gemini; falls back to mock if LLM is unavailable. |
| **Implementation pipeline** | Upload files → infer signals/F3iche → verify F3iche match → target structure → map file → validate → import plan. Company profile is updated along the way. |
| **Dev Test session** | One-click test session at `/dev/test`: creates a project + client, returns company/user slug and project ID so you can test without Firebase or signup. |
| **Resolver & onboarding** | Resolve project by slug (`/api/resolve/slug/{slug}`). Onboarding: check slug, complete onboarding. |
| **Health Check** | Submit questionnaire; optional Temporal workflow; capture interest and report status. |
| **Config & Config-Apply agents** | Start config workflow, answer questions by layer, check status. Config-Apply launches downstream agent for applying config. |
| **Migration** | Get upload URL, start analysis, poll status, confirm mapping. For data migration workflows. |
| **Ingest** | Upload and ingest files (e.g. for discovery or implementation). |
| **Deploy / Infra** | Trigger infrastructure deployment (e.g. deploy/infra) for a project. |
| **Auth** | Firebase sync and user resolution; graceful behaviour when Firebase is not configured. |
| **Mission Control (Home)** | Project home with links to Upload, Validate, Data Mapper, Testing Suite, Discovery, Config, Infra, Ingestion, Migration, etc. |

---

## What you’ll see (output)

| When you… | Output in the app (UI) | Output in the terminal / API |
|-----------|------------------------|-------------------------------|
| **Start backend** | — | `Using SQLite: ...` then `Uvicorn running on http://0.0.0.0:8000`. |
| **Start frontend** | — | `Local: http://localhost:3000`. |
| **Open app** | Landing page at localhost:3000; login/signup or “Firebase not configured” + link to Dev Test. | — |
| **Use Dev Test** | Redirect to `/{companySlug}/{userSlug}/home` with project context; Mission Control with tiles. | Backend: test session created; optional log. |
| **Open Discovery** | Chat UI: “Welcome to F3Next…” then bot questions (industry → make-to-order → turnover → current system → pain point). After 5 steps, recommendation (ERP, fit score, etc.) or timeout message if worker not running. | Discovery worker: SQL updates, activity logs. Temporal: workflow events. |
| **Send a Discovery message** | “Thinking…” then bot reply (or after ~90 s: message to start Temporal + worker). | Worker: `analyze_discovery_turn`, `save_discovery_state`; DB updates. |
| **Use Implementation (Upload)** | Upload screen; after upload, success or error. | Backend: implementation upload endpoint logs. |
| **Use Implementation (Validate / Map)** | Validation UI or mapping result. | Backend: `/api/implementation/validate`, `/map-file`, etc. |
| **Call API docs** | — | Open http://localhost:8000/docs: Swagger UI with all routes (discovery, health_check, implementation, dev, etc.). |
| **Health Check submit** | Success message; stored report/project_id in localStorage. | Backend: health_check submit; optional workflow. |
| **Config / Config-Apply start** | Status or next step in UI. | Backend: `[Config]` / `[ConfigApply]` logs; Temporal if used. |

---

## Quick run (see output clearly)

Open **4–5 terminals** and keep them visible so you can see logs from each part.

### Terminal 1: Backend (FastAPI)

```powershell
cd D:\ERPNext
.\venv\Scripts\Activate
.\backend\run.ps1
```

**Expected output:** `Uvicorn running on http://0.0.0.0:8000`  
**Check:** Open [http://localhost:8000/docs](http://localhost:8000/docs) — API docs should load.

---

### Terminal 2: Frontend (Next.js)

```powershell
cd D:\ERPNext\frontend
npm install
npm run dev
```

**Expected output:** `Local: http://localhost:3000`  
**Check:** Open [http://localhost:3000](http://localhost:3000) — landing page loads.

---

### Terminal 3: Temporal server (required for Discovery chat)

```powershell
temporal server start-dev
```

**Expected output:** `Temporal server started` and gRPC on `127.0.0.1:7233`.  
Leave this running. Without it, Discovery chat will not advance past “Thinking…”.

---

### Terminal 4: Discovery worker (processes Discovery chat turns)

```powershell
cd D:\ERPNext
.\venv\Scripts\Activate
python -m containers.discovery.worker
```

**Expected output:** `Discovery Agent Container: Online & Listening...`  
**Check:** When you use Discovery chat in the app, this terminal shows SQL and activity logs. If this is not running, the chat stays on “Thinking…” until the 90s timeout.

---

### Terminal 5 (optional): Ollama (local LLM)

If you want real AI responses instead of mocks:

```powershell
ollama pull llama3.2:1b
ollama serve
```

If Ollama is not running or the model is too large for your RAM, the app uses **mock responses** so the flow still completes. To force mock-only, set in `.env`:

```env
OLLAMA_FALLBACK=true
```

---

## Environment

Create `.env` in the project root (copy from `.env.example` if present):

```env
# Backend
DATABASE_URL=sqlite+aiosqlite:///./f3next.db
# Or PostgreSQL: postgresql+asyncpg://postgres:password@localhost:5432/f3next_db

# Ollama (optional)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:1b

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Where to see what

| What you do            | Where to look for output                          |
|------------------------|---------------------------------------------------|
| Backend API requests   | Terminal 1 (uvicorn)                             |
| Frontend / React       | Browser dev tools (F12) + Terminal 2 (Next.js)   |
| Discovery chat flow   | Terminal 4 (Discovery worker) + Terminal 3 (Temporal) |
| Ollama / mock         | Terminal 4 (worker logs); Terminal 5 if using Ollama |

---

## Feature verification checklist

After starting the services above, use this list to confirm everything works:

| Feature | How to verify |
|--------|----------------|
| **Backend API** | [http://localhost:8000/docs](http://localhost:8000/docs) loads; try `GET /health` or any endpoint. |
| **Frontend** | [http://localhost:3000](http://localhost:3000) loads; landing, login, and nav work. |
| **Dev Test session** | Go to `/dev/test` (or link from login when Firebase is not configured); get a test project and slug. |
| **Discovery chat** | From a project page open **Discovery**; send a message. Bot replies if Temporal + Discovery worker are running. |
| **Mission Control / Home** | From project home you can open Upload, Validate, Data Mapper, Testing Suite, Discovery, Config, etc. |
| **API URL fallback** | If `NEXT_PUBLIC_API_URL` is unset, frontend still calls `http://localhost:8000` (no "Failed to fetch" from undefined). |

---

## Test the flow

1. **Backend + Frontend:** Go to [http://localhost:3000](http://localhost:3000) → use **Dev Test** or sign up / log in.
2. **Discovery chat:** Open a project → **Discovery** → send a message.  
   - If **Temporal** and the **Discovery worker** are running, the bot reply appears after a short delay.  
   - If not, after ~90 seconds you’ll see a message asking you to start the worker and Temporal.

---

## Troubleshooting

- **Backend: "No module named 'app'"** — Run the backend from the `backend` folder or use `.\backend\run.ps1` from the repo root (it sets `PYTHONPATH`).
- **Backend: "No module named 'shared'"** — Repo root must be on `PYTHONPATH` when running uvicorn; `run.ps1` / `run.bat` do this. If you run uvicorn manually, set `PYTHONPATH=D:\ERPNext\backend` (or your path) and run from `backend`.
- **UnicodeEncodeError / emoji in console** — Backend and discovery launcher use ASCII-only log messages so they work on Windows (e.g. cp1252) without changing system locale.
- **Discovery stuck on "Thinking..."** — Start **Temporal** (`temporal server start-dev`) and the **Discovery worker** (`python -m containers.discovery.worker`). Check their terminals for errors.
- **"Failed to fetch"** — Ensure backend is running on port 8000 and, if needed, set `NEXT_PUBLIC_API_URL=http://localhost:8000` in `.env` or `.env.local` for the frontend.

---

## Scripts reference

| Script              | Purpose                          |
|---------------------|----------------------------------|
| `.\backend\run.ps1` | Start backend (from repo root)   |
| `.\backend\run.bat` | Same, from cmd                   |
| `run-temporal.bat`  | Start Temporal dev server        |
| `python -m containers.discovery.worker` | Start Discovery worker |

---

## Branch and repo

- **Branch:** `Implem_agent`  
- **Repo:** https://github.com/AllBLUE-24/F3Next  

To push your work to this branch:

```powershell
git checkout Implem_agent
git merge Parth-works
git push origin Implem_agent
```

Or push your current branch and open a Pull Request into `Implem_agent`.
