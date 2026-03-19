# F3Next — Full Quick Start in VS Code

Complete step-by-step guide to run the app from scratch in VS Code.

---

## Step 0: Prerequisites (Install Once)

### 1. Install Python 3.10+
- Download: https://www.python.org/downloads/
- During install, check **"Add Python to PATH"**
- Verify: Open terminal → `python --version`

### 2. Install Node.js 18+
- Download: https://nodejs.org/
- Verify: `node --version` and `npm --version`

### 3. Install Docker Desktop (for PostgreSQL)
- Download: https://www.docker.com/products/docker-desktop/
- Start Docker Desktop and ensure it's running

### 4. Install Ollama (local LLM)
- Download: https://ollama.ai
- Install and run Ollama

---

## Step 1: Open Project in VS Code

1. Open VS Code
2. **File → Open Folder** → select `d:\ERPNext`
3. Open the integrated terminal: **Terminal → New Terminal** (or `` Ctrl+` ``)

---

## Step 2: Start Ollama

In **Terminal 1** (or a separate terminal):

```powershell
ollama serve
```

Leave this running. In another terminal:

```powershell
ollama pull llama3.2
```

*(First pull may take a few minutes. You can use `llama2` or `mistral` if preferred.)*

---

## Step 3: Start PostgreSQL (Docker)

In **Terminal 1** (or a new terminal in VS Code):

```powershell
cd d:\ERPNext
docker-compose -f docker-compose.postgres.yml up -d
```

Verify it's running:
```powershell
docker ps
```
*(You should see `f3next-postgres` container.)*

---

## Step 4: Create Python Virtual Environment & Install Dependencies

In the VS Code terminal:

```powershell
cd d:\ERPNext
python -m venv venv
.\venv\Scripts\Activate
```

*(You should see `(venv)` in the prompt.)*

```powershell
pip install -r backend/requirements.txt
```

*(This may take 2–5 minutes.)*

---

## Step 5: Verify .env File

Ensure `d:\ERPNext\.env` exists with:

```
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/f3next_db
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
NEXT_PUBLIC_API_URL=http://localhost:8000
```

*(The `.env` file is already in the project. Adjust `DATABASE_URL` if you changed the PostgreSQL password.)*

---

## Step 6: Run Database Migration (One-Time)

**Option A — If you have `psql` installed:**
```powershell
psql -U postgres -h localhost -d f3next_db -f d:\ERPNext\backend\migrations\add_implementation_columns.sql
```

**Option B — Using Docker:**
```powershell
Get-Content d:\ERPNext\backend\migrations\add_implementation_columns.sql | docker exec -i f3next-postgres psql -U postgres -d f3next_db
```

**Option C — Skip for now:** The backend creates base tables on first run. Run this migration later if you get errors about missing columns.

---

## Step 7: Run the Backend

In **Terminal 1** (with venv activated):

```powershell
cd d:\ERPNext\backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

You should see:
```
🚀 App starting: Verifying database tables...
✅ Database tables verified/created.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**Test:** Open http://localhost:8000/docs in a browser.

---

## Step 8: Run the Frontend (New Terminal)

**Terminal → New Terminal** (or split terminal: `` Ctrl+Shift+` ``)

```powershell
cd d:\ERPNext\frontend
npm install
npm run dev
```

You should see:
```
▲ Next.js 16.x.x
- Local: http://localhost:3000
```

**Test:** Open http://localhost:3000 in a browser.

---

## Step 9: Verify Everything Works

1. **Backend API:** http://localhost:8000/docs  
   - Try `GET /api/implementation/f3iche/list`

2. **Frontend:** http://localhost:3000  
   - Landing page should load

---

## Summary: What to Run (In Order)

| Order | Terminal | Command |
|-------|----------|---------|
| 1 | Terminal 1 | `ollama serve` *(keep running)* |
| 2 | Terminal 2 | `ollama pull llama3.2` *(one-time)* |
| 3 | Terminal 2 | `cd d:\ERPNext` then `docker-compose -f docker-compose.postgres.yml up -d` |
| 4 | Terminal 2 | `cd d:\ERPNext` → `.\venv\Scripts\Activate` → `cd backend` → `python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload` *(keep running)* |
| 5 | Terminal 3 | `cd d:\ERPNext\frontend` → `npm run dev` *(keep running)* |

---

## VS Code Tips

- **Split terminal:** Click the split icon in the terminal panel, or `` Ctrl+Shift+` ``
- **Run multiple terminals:** You need at least 2–3 terminals (Ollama optional if not using Discovery)
- **Python interpreter:** `Ctrl+Shift+P` → "Python: Select Interpreter" → choose `.\venv\Scripts\python.exe`

---

## Troubleshooting

| Error | Fix |
|-------|-----|
| `DATABASE_URL is None` | Ensure `.env` is at `d:\ERPNext\.env` (project root) |
| `connection refused` (PostgreSQL) | Start Docker: `docker-compose -f docker-compose.postgres.yml up -d` |
| `ModuleNotFoundError: shared` | Run backend from `d:\ERPNext\backend` with project root as working directory, or set `PYTHONPATH=d:\ERPNext` |
| `Ollama connection failed` | Run `ollama serve` in a separate terminal |
| Port 8000 already in use | Stop other process or change port: `--port 8001` |
| Port 3000 already in use | Next.js will prompt to use 3001 |
