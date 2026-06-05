# F3Next — AI-Powered ERP Implementation & Operations

> **Automate ERP implementation and operations.** Replace months of consulting and lakhs of cost with minutes of AI-driven setup — no employee training needed.
>
> *the brain of your company - new identity of f3next*

[Live](https://f3next.in)
[GitHub](https://github.com/AllBLUE-24/F3Next)

---

## 🎯 Mission

Traditional ERP implementation is broken — **6 months, ₹5+ lakhs, 70% failure rate**. F3Next replaces this entire pipeline with AI:

1. **AI Consultant** — Recommends the right ERP based on 5–7 smart questions
2. **Automated Deployment** — Cloud ERP instance deployed in minutes, not months
3. **Intelligent Data Migration** — Upload any format; AI maps, validates, and migrates
4. **Prompt-to-Action Operations** — Run your ERP by typing plain English commands

**Zero consultants. Zero training. Fraction of the cost.**

---

## 🏗️ Architecture


| Layer               | Technology                                                                  | Environment          |
| ------------------- | --------------------------------------------------------------------------- | -------------------- |
| **Frontend**        | Next.js 15 (React)                                                          | Vercel               |
| **Backend API**     | FastAPI (Python)                                                            | Render               |
| **Containers**      | Discovery, Implementation, OS, Health Check, Knowledge Base, ERPNext agents | DigitalOcean Droplet |
| **Workflow Engine** | Temporal (Server + Workers)                                                 | DigitalOcean Droplet |
| **Database**        | PostgreSQL                                                                  | Supabase             |
| **Auth**            | Supabase Auth (Email + Google OAuth)                                        | Supabase             |
| **File Storage**    | Cloudflare R2 / AWS S3                                                      | Cloud                |


---

## 🚀 Quick Start (Local Development)

### Prerequisites

- Node.js 18+
- Python 3.11+
- Docker & Docker Compose
- PostgreSQL (or use Supabase)

### 1. Clone & Configure

```bash
git clone https://github.com/AllBLUE-24/F3Next.git
cd F3Next

# Copy environment templates
cp .env.example .env
cp frontend/.env.example frontend/.env.local

# Edit .env and frontend/.env.local with your credentials
```

### 2. Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
# → http://localhost:3000
```

### 4. Containers (Docker)

```bash
# Start Temporal + all agent containers
docker compose up --build
```

---

## 🔧 Environment Configuration

The project is fully environment-driven. All service URLs are configured via `.env` files — **no hardcoded URLs**.


| Variable                        | Description                          | Local                                | Production                          |
| ------------------------------- | ------------------------------------ | ------------------------------------ | ----------------------------------- |
| `NEXT_PUBLIC_API_URL`           | Backend API URL                      | `http://localhost:8000`              | `https://your-backend.onrender.com` |
| `NEXT_PUBLIC_SUPABASE_URL`      | Supabase project URL                 | —                                    | `https://xxx.supabase.co`           |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase anon key                    | —                                    | `eyJ...`                            |
| `DATABASE_URL`                  | PostgreSQL connection string         | `postgresql+asyncpg://...@localhost` | Supabase pooler URL                 |
| `TEMPORAL_HOST`                 | Temporal server address              | `localhost:7233`                     | `<droplet-ip>:7233`                 |
| `ALLOWED_ORIGINS`               | Extra CORS origins (comma-separated) | —                                    | Custom domains                      |


See `.env.example` and `frontend/.env.example` for the full list.

---

## 📁 Project Structure

```
F3Next/
├── frontend/          # Next.js 15 app (Vercel)
│   ├── src/
│   │   ├── app/       # Pages & routes
│   │   ├── components/# UI components
│   │   ├── lib/       # API clients & utilities
│   │   └── utils/     # Supabase helpers
│   └── .env.local     # Frontend env vars
├── backend/           # FastAPI server (Render)
│   └── app/
│       ├── api/       # Route handlers
│       ├── services/  # Business logic
│       └── main.py    # App entrypoint
├── containers/        # Dockerized AI agents
│   ├── discovery/     # ERP recommendation engine
│   ├── implementation/# Data migration workflows
│   ├── os/            # Prompt-to-action operations
│   ├── health_check/  # Operational audit agent
│   ├── knowledge_base/# Domain knowledge retrieval
│   └── erpnext/       # ERPNext integration
├── shared/            # Shared models & DB config
├── .env               # Root environment variables
└── docker-compose.yml
```

---

## 🤝 Contact

- **Phone / WhatsApp**: +91 93709 83966  
- **Email**: [parth.kulkarni2412@gmail.com](mailto:parth.kulkarni2412@gmail.com)  
- **LinkedIn**: [Parth Kulkarni](https://www.linkedin.com/in/parth-kulkarni-f3/)  
- **Website**: [f3next.in](https://f3next.in)

---

## 📜 License

Proprietary. All rights reserved. © 2025 F3Next.