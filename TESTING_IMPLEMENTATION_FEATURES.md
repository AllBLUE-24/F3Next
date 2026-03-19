# Testing Implementation Features (IMPLEMENTATION_SYSTEM_OVERVIEW.md)

This guide maps each feature in `IMPLEMENTATION_SYSTEM_OVERVIEW.md` to how you can test it from the **Mission Control** dashboard (`/test-company/test-user/home`).

---

## Quick Start

1. Go to **Mission Control**: `/test-company/test-user/home` (via **Test app (no login)** on the landing page).
2. Use the module cards to access each feature.

---

## Feature-by-Feature Testing

### 1. Discovery Agent (Step 2 — Consultant Chatbot) ✅ ACTIVE

**IMPLEMENTATION_SYSTEM_OVERVIEW:** Consultant chatbot that asks about company size, industry, processes, pain points; recommends ERP; outputs F3iche + Industry.

**How to test:**
- Click **Discovery Agent** on Mission Control.
- You’ll land on `/test-company/test-user/discovery`.
- Chat with the agent (Ollama must be running; see `.env` for `OLLAMA_BASE_URL`).
- Discovery writes F3iche + Industry into `Hook.discovery_metadata`.

**Backend:** `/api/discovery/chat`, `/api/discovery/status/{projectId}`

---

### 2. Data Mapper (Steps 3–4, 9 — Signals, F3iche Verification, Mapping) ✅ UNLOCKED

**IMPLEMENTATION_SYSTEM_OVERVIEW:**
- Step 3: `signals_registry.json` infers F3iche from uploaded files.
- Step 4: F3iche match verification (user vs system).
- Step 9: Map user data to ERPNext doctypes/fields.

**How to test:**
- Click **Data Mapper** on Mission Control.
- You’ll land on `/test-company/test-user/upload` (Implementation flow start).
- **Upload** → Upload CSV/Excel files.
- **Analyze** → System infers F3iche from files, maps to ERPNext.
- **Validate** → Validation report.
- **Sandbox** → Test instance (if deployed).

**Flow:** Upload → Analyze → Validate → Sandbox

**Backend APIs:**
- `POST /api/implementation/signals/infer` — Infer F3iche from files
- `POST /api/implementation/f3iche/verify` — Verify user vs signals F3iche
- `POST /api/implementation/map-file` — Map file content to ERPNext
- `GET /api/implementation/profile/{project_id}` — Company profile

**Note:** Upload uses local storage when `USE_LOCAL_STORAGE=true`. Ensure backend is running.

---

### 3. Testing Suite (Step 10 — Validation) ✅ UNLOCKED

**IMPLEMENTATION_SYSTEM_OVERVIEW:** Validation of mappings and data (types, required fields, referential integrity, business rules).

**How to test:**
- Click **Testing Suite** on Mission Control.
- You’ll land on `/test-company/test-user/validate`.
- Or go through Data Mapper: Upload → Analyze → Validate.

**Backend:** `POST /api/implementation/validate`

---

### 4. Target Structure (Step 8) — Backend Only

**IMPLEMENTATION_SYSTEM_OVERVIEW:** Action workflow (what to create, in what order).

**How to test:**
- No dedicated UI; used internally by Analyze/Validate.
- Direct API: `POST /api/implementation/target-structure` with `project_id`, `f3iche`, `industry`.

---

### 5. Import Plan (Step 11 — 3-Phase Import) — Backend Only

**IMPLEMENTATION_SYSTEM_OVERVIEW:** Config → Master → Transactional import plan.

**How to test:**
- No dedicated UI; used after validation.
- Direct API: `POST /api/implementation/import/plan`

---

### 6. ERP Selector — Coming Soon

**IMPLEMENTATION_SYSTEM_OVERVIEW:** AI-driven ERP comparison and recommendation. Not yet implemented.

---

### 7. Infrastructure Services

| Service           | Purpose                          | Test Notes                                      |
|-------------------|----------------------------------|-------------------------------------------------|
| **AWS Console**   | Cloud instances                  | External link; not part of F3Next app.          |
| **MinIO Storage** | Object storage                   | With `USE_LOCAL_STORAGE=true`, uploads go to `uploads/`. |
| **Instance Settings** | Project-level config        | Placeholder; no UI yet.                         |

---

## End-to-End Test Flow

1. **Discovery** → Chat with Discovery Agent; get F3iche + Industry.
2. **Data Mapper** → Upload files → Analyze (signals inference, mapping) → Validate.
3. **Testing Suite** → Review validation report (or jump to Validate from Mission Control).
4. **Sandbox** → If a sandbox exists, test the instance and approve.

---

## Prerequisites

- **Backend:** `cd backend && uvicorn app.main:app --reload`
- **Frontend:** `cd frontend && npm run dev`
- **Ollama:** For Discovery; set `OLLAMA_BASE_URL` in `.env`
- **SQLite:** Default with `USE_SQLITE=true`; DB at `f3next.db`

---

## API Quick Reference

| Endpoint                               | Purpose                    |
|----------------------------------------|----------------------------|
| `GET /api/implementation/profile/{id}` | Get company profile        |
| `POST /api/implementation/signals/infer` | Infer F3iche from files  |
| `POST /api/implementation/f3iche/verify` | Verify F3iche match     |
| `POST /api/implementation/target-structure` | Build target structure |
| `POST /api/implementation/map-file`    | Map file to ERPNext        |
| `POST /api/implementation/validate`    | Validate mapped data       |
| `POST /api/implementation/import/plan` | Build 3-phase import plan  |
| `GET /api/implementation/f3iche/list`   | List available F3iches     |
