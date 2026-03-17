# F3Next — How to Run the Application

## Prerequisites

1. **Python 3.10+** with venv
2. **Node.js 18+** and npm
3. **PostgreSQL** (with `asyncpg`-compatible URL, e.g. `postgresql+asyncpg://user:pass@host:5432/db`)
4. **.env file** at project root with required variables

---

## 1. Environment Setup

Copy `.env.example` to `.env` or create `.env` in the project root:

```env
# Required
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/f3next_db

# LLM: Ollama (local — no API key)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000
```

**Ollama:** Run `ollama serve` in one terminal, then `ollama pull llama3.2` (or llama2, mistral).

---

## 2. Start PostgreSQL (if not running)

**Docker:**
```bash
docker-compose -f docker-compose.postgres.yml up -d
```

See **POSTGRES_SETUP.md** for other options (local install, etc.).

---

## 3. Database Migration (one-time)

```bash
# Using psql (adjust for your DB)
psql -U postgres -d f3next_db -f backend/migrations/add_implementation_columns.sql
```

Or run the SQL manually:
```sql
ALTER TABLE projects ADD COLUMN IF NOT EXISTS implementation_profile JSONB;
ALTER TABLE hooks ADD COLUMN IF NOT EXISTS discovery_metadata JSONB;
```

---

## 4. Run the Backend

**Option A — From project root (recommended):**
```bash
cd d:\ERPNext
pip install -r backend/requirements.txt   # if not done
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Option B — Using run script (Windows):**
```bash
cd d:\ERPNext\backend
run.bat
```

Backend will be at **http://localhost:8000**

- API docs: http://localhost:8000/docs
- Implementation APIs: http://localhost:8000/api/implementation/

---

## 5. Run the Frontend

```bash
cd d:\ERPNext\frontend
npm install
npm run dev
```

Frontend will be at **http://localhost:3000**

---

## 5. Quick Test — Implementation APIs

With the backend running, you can test the implementation system:

**List F3iches:**
```bash
curl http://localhost:8000/api/implementation/f3iche/list
```

**Infer F3iche from files:**
```bash
curl -X POST http://localhost:8000/api/implementation/signals/infer \
  -H "Content-Type: application/json" \
  -d '{"project_id": "00000000-0000-0000-0000-000000000000", "uploaded_files": [{"file_name": "invoice.csv"}]}'
```

**Build target structure:**
```bash
curl -X POST http://localhost:8000/api/implementation/target-structure \
  -H "Content-Type: application/json" \
  -d '{"project_id": "00000000-0000-0000-0000-000000000000", "f3iche": "trading", "industry": "Electronics"}'
```

---

## 7. Full Flow (Discovery + Implementation)

1. **Start backend** (port 8000) and **frontend** (port 3000)
2. **Login/Signup** — requires Firebase config in `.env` for auth
3. **Discovery** — Go to `/{companySlug}/{userSlug}/discovery` and chat; at the end you get F3iche + Industry
4. **Implementation** — Go to `/{companySlug}/{userSlug}/(Implementation)/upload` to upload files
5. The implementation APIs (`/api/implementation/*`) are used by the frontend for signals, mapping, validation, import plan

---

## 8. Optional: Temporal Workers (Discovery, Config, etc.)

For the **Discovery chatbot** and other Temporal workflows to work, you need:

1. **Temporal Server** running (Docker or local)
2. **Discovery worker** started
3. **ERPNext config workers** if using config flow

See `containers/` for worker setup. The backend API will accept requests, but workflows won’t complete without workers.

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `DATABASE_URL not found` | Add `.env` at project root with `DATABASE_URL` |
| `ModuleNotFoundError: shared` | Run backend from project root or ensure `PYTHONPATH` includes project root |
| `relation "projects" does not exist` | Run DB migrations; ensure tables exist |
| Discovery chat doesn’t respond | Start Temporal + Discovery worker |
| Frontend can’t reach API | Set `NEXT_PUBLIC_API_URL=http://localhost:8000` in frontend `.env.local` |
