# F3Next Architecture & Directory Structure

## 🏗 High-Level Architecture
F3Next is a distributed system consisting of a modern web frontend, a fast REST API, and a fleet of asynchronous AI workers orchestrated by Temporal.

| Layer | Technology | Role |
|-------|-----------|------|
| **Frontend** | Next.js 15 (React), TailwindCSS | User Interface (Mission Control, Dashboard, Terminal) |
| **Backend API** | FastAPI (Python) | Main gateway, handling auth resolution and proxying workflow requests |
| **Workflow Engine** | Temporal.io | Orchestrates distributed agent tasks reliably (retries, state management) |
| **Workers** | Python (Temporal Workers) | Execute actual AI logic (Discovery, OS commands, Data mapping) |
| **Database** | PostgreSQL (Supabase) | Stores application state, user profiles, and chat histories |
| **Proxy / Gateway** | Caddy | Reverse proxy handling SSL and routing `/api/*` to FastAPI |

---

## 📁 Directory Breakdown

### `/frontend` (The UI Layer)
- **`src/app/`**: Next.js App Router. Contains the main pages (`/login`, `/onboarding`, `/[companySlug]/[userSlug]/home`).
- **`src/components/`**: Reusable React components (UI elements, Layouts, Chat windows).
- **`src/lib/api/`**: Universal fetch clients. These are strictly configured to use **relative paths** (`/api/...`) so Caddy can proxy them to the backend, avoiding CORS and hardcoded IP issues.
- **`src/utils/supabase/`**: Next.js middleware and client helpers for Supabase Authentication.

### `/backend` (The API Gateway)
- **`app/main.py`**: The FastAPI entry point. Mounts all routers.
- **`app/api/`**: Route definitions (`/api/discovery`, `/api/os_command`, `/api/implementation`).
- **Function:** Acts as a fast, synchronous bridge between the Next.js frontend and the asynchronous Temporal workflows.

### `/containers` (The AI Workers)
Contains isolated Docker environments for each specialized Temporal Worker.
- **`discovery/`**: Runs the Discovery Agent workflow.
- **`implementation/`**: Runs the Data Mapping and Validation workflow.
- **`os/`**: Runs the Command/Terminal operations workflow.
- **`erpnext/`**: Specialized worker for integrating directly with ERPNext APIs.
- **`health_check/`**: Runs automated diagnostics.

### `/shared` (Common Data Layer)
- **`models/`**: SQLAlchemy ORM models (`ISSession`, `Client`, `Project`).
- **`database/db.py`**: Database connection logic.
- **Function:** Shared by both the FastAPI backend and all the Temporal workers to ensure consistent database reads/writes without duplicating code.

### Root Infrastructure
- **`docker-compose.yml`**: Spins up the entire stack (Temporal server, all Python workers, Backend API, Frontend Next.js, and Caddy).
- **`Caddyfile`**: Configuration for the Caddy reverse proxy to route traffic seamlessly.
