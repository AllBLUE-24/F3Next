# F3Next — Complete System Architecture

> F3Next is an **autonomous ERP deployment and operations platform**. It ingests a company's raw data, intelligently maps it to ERPNext, deploys the ERP system, and then lets users control it via natural language commands — all orchestrated by Temporal workflows.

---

## 🗺️ System Overview — How Every Service Connects

```mermaid
graph TB
    subgraph USER["👤 User"]
        Browser["Browser\n(Next.js Frontend)"]
    end

    subgraph EDGE["🌐 Edge / Ingress"]
        Caddy["Caddy\nReverse Proxy\n:80 / :443"]
    end

    subgraph API["⚡ Backend API"]
        FastAPI["FastAPI\n(backend/app/main.py)\n/api/*"]
    end

    subgraph TEMPORAL["🔄 Temporal Orchestration Engine"]
        TServer["Temporal Server\n:7233"]
        TUI["Temporal UI\n:8080"]
        TDB["Temporal Postgres\n(internal state)"]
    end

    subgraph WORKERS["🤖 AI Worker Fleet (Docker)"]
        Discovery["Discovery Worker\ndiscovery-queue"]
        IS["Implementation Worker\nis-queue"]
        OS["OS Worker\nos-main-queue\nos-execute-queue\nos-search-queue\nos-analyze-queue"]
        CVS["CVS Worker\ncvs-main-queue"]
        CVSPoller["CVS Poller\n(cron trigger)"]
        CVSRecovery["CVS Recovery\n(stuck events)"]
        ERPInfra["ERPNext Infra Worker\nerpnext-infra-queue"]
        HealthCheck["Health Check Worker"]
        KBSeeder["Knowledge Base Seeder\n(one-shot on deploy)"]
    end

    subgraph SHARED_INFRA["🏗️ Shared Infrastructure"]
        Redis["Redis\n:6379\n(RAG cache + session cache)"]
        Supabase["Supabase / PostgreSQL\n(application state + pgvector KB)"]
        R2["Cloudflare R2\n(file storage — CSVs, manifests, profiles)"]
        OpenAI["OpenAI API\n(embeddings: text-embedding-3-large)"]
        LLMProviders["LLM Providers\nGemini Flash / GPT-4o-mini\n(round-robin key rotation)"]
    end

    subgraph EXTERNAL["🏢 External Systems"]
        ERPNext["Customer ERPNext Instance\n(Frappe / ERPNext API)"]
        Prometheus["Prometheus\n:9090"]
        Grafana["Grafana\n:3001"]
    end

    %% User → Edge → API
    Browser -->|"HTTPS"| Caddy
    Caddy -->|"/api/* proxy"| FastAPI
    Caddy -->|"/ proxy"| Browser

    %% API → Temporal
    FastAPI -->|"start_workflow / signal / query"| TServer
    TServer --- TDB
    TServer --- TUI

    %% Temporal → Workers
    TServer -->|"discovery-queue"| Discovery
    TServer -->|"is-queue"| IS
    TServer -->|"os-main/execute/search/analyze-queue"| OS
    TServer -->|"cvs-main-queue"| CVS
    TServer -->|"cvs-main-queue"| CVSPoller
    TServer -->|"cvs-main-queue"| CVSRecovery

    %% Workers → Shared Infra
    Discovery --> Supabase
    Discovery --> LLMProviders
    IS --> Supabase
    IS --> R2
    IS --> LLMProviders
    OS --> Supabase
    OS --> Redis
    OS --> LLMProviders
    CVS --> Supabase
    CVS --> R2
    CVS --> Redis
    KBSeeder --> Supabase
    KBSeeder --> OpenAI

    %% Workers → External
    IS --> ERPNext
    CVS --> ERPNext
    ERPInfra --> ERPNext
    ERPNext -->|"Frappe Webhooks"| FastAPI

    %% Monitoring
    FastAPI --> Prometheus
    OS --> Prometheus
    CVS --> Prometheus
    Prometheus --> Grafana

    %% Context Engine (shared by OS + CVS)
    OS -->|"3-tier context lookup"| Redis
    OS -->|"CVS snapshot read"| Supabase
```

---

## 🧱 Layer Architecture

| Layer | Service | Technology | Role |
|-------|---------|-----------|------|
| **Frontend** | `frontend_web` | Next.js 15, React, TailwindCSS | Mission Control UI, Discovery Chat, OS Terminal |
| **Reverse Proxy** | `caddy` | Caddy v2 | SSL termination, routes `/api/*` → FastAPI, `/` → Next.js |
| **API Gateway** | `backend_api` | FastAPI (Python) | Synchronous bridge: auth, workflow launch, signal relay |
| **Orchestrator** | `temporal` | Temporal.io | Durable workflow execution, retry, state management |
| **Discovery Agent** | `discovery_worker` | Python + Temporal | AI consultant "Adi" — business profiling chat |
| **Implementation System** | `implementation_worker` | Python + Temporal | 14-step ERP onboarding pipeline |
| **OS Agent** | `os_worker` | Python + Temporal | Natural language → ERP command execution |
| **Context Versioning** | `cvs_worker` + `cvs_poller` | Python + Temporal | Keeps company context snapshots fresh from ERPNext |
| **Context Engine** | `shared/context_engine/` | Python | 3-tier context loader (static + f3iche + CVS live data) |
| **LLM Router** | `llm_router.py` | LangChain + OpenAI/Gemini | Provider-agnostic LLM with key rotation & fallback |
| **Knowledge Base** | `containers/knowledge_base/` | pgvector (PostgreSQL) | APQC + ERPNext docs + F3iche domain knowledge |
| **Cache** | `redis` | Redis 7 | RAG query cache, OS session context cache |
| **Database** | Supabase | PostgreSQL 15 | All application state (projects, sessions, CVS snapshots) |
| **File Storage** | Cloudflare R2 | S3-compatible | Raw uploads, parsed manifests, mapped data, import plans |
| **Observability** | `prometheus` + `grafana` | Prometheus + Grafana | LLM health, latency, pipeline metrics |

---

## 🔄 End-to-End User Journey

```mermaid
sequenceDiagram
    participant User
    participant UI as Next.js UI
    participant API as FastAPI
    participant T as Temporal
    participant D as Discovery Worker
    participant IS as Implementation Worker
    participant CVS as CVS Worker
    participant OS as OS Worker
    participant ERP as ERPNext

    Note over User,ERP: Phase 1 — Discovery (Business Profiling)
    User->>UI: Visits /onboarding
    UI->>API: POST /api/discovery/start
    API->>T: start_workflow(DiscoveryChatWorkflow)
    T->>D: Execute workflow
    D-->>UI: "Hi, I'm Adi..." (polling)
    User->>UI: Answers questions
    UI->>API: POST /api/discovery/reply
    API->>T: signal(receive_user_reply)
    T->>D: analyze_discovery_turn → update coverage
    Note over D: Loop until coverage complete
    D->>T: generate_erp_recommendation
    D->>Supabase: save discovery_metadata (f3iche, industry, ERP fit)

    Note over User,ERP: Phase 2 — Implementation (ERP Deployment)
    User->>UI: Uploads company data files
    UI->>API: POST /api/implementation/start
    API->>T: start_workflow(ImplementationWorkflow)
    T->>IS: Execute 14-step pipeline
    IS->>R2: Virus scan → store clean files
    IS->>IS: Infer F3iche from data signals
    User->>UI: Confirms business type
    API->>T: signal(f3iche_confirmed)
    IS->>IS: Build profile → map files → validate
    User->>UI: Reviews mappings
    API->>T: signal(mapping_confirmed)
    IS->>IS: Build import plan
    User->>UI: Approves sandbox
    API->>T: signal(sandbox_approved)
    IS->>ERP: Execute Phase A (Config) → B (Master) → C (Transactional)
    IS->>CVS: Trigger CVS force-sync + register webhooks

    Note over User,ERP: Phase 3 — OS (Live ERP Operations)
    User->>UI: Types "Create Sales Order for Acme..."
    UI->>API: POST /api/os/command
    API->>T: start_workflow(ERPOSCommandWorkflow)
    T->>OS: 9-step pipeline
    OS->>OS: extract_intent → ambiguity loop
    OS->>CVS: retrieve_context (company snapshot)
    OS->>OS: plan_command → generate_payload → validate
    OS->>User: Confirmation gate (for high-risk ops)
    OS->>ERP: execute_command (ERPNext API call)
    OS->>OS: format_result
    OS-->>UI: Human-readable response
    ERP-->>CVS: Webhook → update context snapshot
```

---

## 📁 Repository Structure

```
F3Next/
├── ARCHITECTURE.md                  ← This file
├── docs/
│   ├── ARCH_OS.md                   ← OS Agent deep-dive
│   ├── ARCH_DISCOVERY.md            ← Discovery Agent deep-dive
│   ├── ARCH_IMPLEMENTATION.md       ← Implementation System deep-dive
│   ├── ARCH_CVS.md                  ← Context Versioning Service deep-dive
│   └── ARCH_CONTEXT_ENGINE.md       ← Shared Context Engine deep-dive
│
├── frontend/                        ← Next.js 15 UI
├── backend/                         ← FastAPI gateway
├── containers/
│   ├── os/                          ← OS Agent Worker
│   ├── discovery/                   ← Discovery Agent Worker
│   ├── implementation/              ← Implementation System Worker
│   ├── context_versioning/          ← CVS Worker + Poller + Recovery
│   ├── knowledge_base/              ← KB seeding scripts
│   ├── erpnext/                     ← ERPNext infra worker
│   └── health_check/                ← Health diagnostics worker
├── shared/
│   ├── context_engine/              ← 3-tier context loading
│   ├── llm_providers/               ← OpenAI + Gemini provider abstraction
│   ├── erp_adapters/                ← ERP-specific API adapters
│   ├── models/                      ← SQLAlchemy ORM models
│   ├── database/                    ← DB connection (async + sync)
│   ├── embedding_generator.py       ← OpenAI embedding w/ key rotation
│   ├── rag_cache.py                 ← Redis-backed RAG cache
│   └── r2_client.py                 ← Cloudflare R2 file operations
├── llm_router.py                    ← Universal LLM router (root-level)
├── docker-compose.yml               ← Full stack definition
├── Caddyfile                        ← Reverse proxy config
└── monitoring/                      ← Prometheus + Grafana configs
```

---

## 🔑 Key Design Principles

1. **Temporal-First Orchestration** — All multi-step business logic runs inside Temporal workflows. Activities are retried automatically; workflows survive crashes.

2. **Human-in-the-Loop Signals** — Temporal `signal` primitives allow the UI to inject user decisions (confirmations, clarifications) into running workflows mid-execution.

3. **3-Tier Context Architecture** — The Context Engine assembles company context from three layers: static ERP schema (Tier 1), industry/f3iche templates (Tier 2), and live CVS snapshots from ERPNext (Tier 3).

4. **Event-Driven Context Freshness** — CVS worker listens to Frappe webhooks from customer ERPNext instances and triggers snapshot rebuilds automatically whenever data changes.

5. **Provider-Agnostic LLM** — `llm_router.py` provides a single interface backed by Gemini Flash and GPT-4o-mini with automatic key rotation, quota sidetracking, and cross-provider fallback.

6. **Zero-Hardcode Policy** — Frontend uses only relative `/api/*` paths; all ERP URLs and credentials are resolved from the database at runtime.

---

*For detailed flowcharts of each subsystem, see the `docs/` directory.*
