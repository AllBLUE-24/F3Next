# LLM Router & Shared Infrastructure — Architecture & Flow

> This document covers the cross-cutting infrastructure shared by all F3Next services: the LLM router, embedding generator, RAG cache, R2 file client, and the shared database + model layer.

---

## 🤖 LLM Router (`llm_router.py`)

The LLM Router is a **universal, provider-agnostic AI gateway** used by all containers. It handles key rotation, quota sidetracking, model tier fallback, and cross-provider fallback transparently.

### Architecture

```mermaid
graph TB
    subgraph CALLERS["Callers"]
        OS["OS Agent\nclarity_agent, result_formatter\nbusiness_analyzer"]
        IS["IS Agent\nsignals, profile, target\nmapping, LLM helper"]
        DISC["Discovery Agent\nanalyze_discovery_turn\ngenerate_recommendation"]
    end

    subgraph ROUTER["llm_router.py"]
        INVOKE["invoke_smart_llm(messages, model_name)
        invoke_smart_llm_sync(messages, model_name)
        invoke_agentic_loop(prompt, tools, schema)"]

        MODEL_Q["_build_model_queue(requested_model)
        ────────────────────────────────────────────
        e.g. requested = 'gpt-4o-mini'
        queue = ['gpt-4o-mini', 'gpt-4o', 'gpt-4-turbo',
                 'gemini-2.5-flash', 'gemini-1.5-flash-latest'...]
        (cross-provider fallback included)"]

        KEY_SEL["_select_key_list(task_type, model)
        ──────────────────────────────────────────
        task_type=simple → OPENAI_API_KEYS
        task_type=complex → OPENAI_API_KEYS_COMPLEX
        (same for Gemini variants)"]

        QUOTA["Per-(model, key) Quota Tracker
        _quota_sidelined: Dict[(model, key), timestamp]
        ─────────────────────────────────────────────────
        On 429/quota error → sideline key for 60s
        On retry → skip sidelined keys
        After cooldown → re-admit key"]

        CALL["_try_model_async / _try_model_sync
        ──────────────────────────────────────────
        For each available key (not sidelined):
          Build LangChain LLM object (ChatOpenAI / ChatGoogleGenerativeAI)
          Call llm.ainvoke(messages) or llm.invoke(messages)
          On quota error → sideline key, try next
          On success → return normalised response"]
    end

    subgraph PROVIDERS["LLM Providers"]
        OPENAI_P["OpenAI\ngpt-4o-mini (default)\ngpt-4o, gpt-4-turbo"]
        GEMINI_P["Google Gemini\ngemini-2.5-flash (default)\ngemini-1.5-flash-latest\ngemini-1.5-pro-latest"]
    end

    subgraph AGENTIC["Agentic Loop (invoke_agentic_loop)"]
        OPENAI_PROV["OpenAIProvider\n(tool calling via function calling API)"]
        GEMINI_PROV["GeminiProvider\n(tool calling via Gemini function declarations)"]
    end

    OS & IS & DISC --> INVOKE
    INVOKE --> MODEL_Q --> KEY_SEL --> QUOTA --> CALL
    CALL --> OPENAI_P & GEMINI_P
    INVOKE -->|"agentic"| OPENAI_PROV & GEMINI_PROV
```

### Model Tier Fallback Chain

```mermaid
flowchart LR
    REQ["Request:\nmodel='gpt-4o-mini'"] --> TRY1

    TRY1["Try gpt-4o-mini\n(all OPENAI keys)"] -->|"All keys 429"| TRY2
    TRY2["Try gpt-4o\n(all OPENAI keys)"] -->|"All keys 429"| TRY3
    TRY3["Try gpt-4-turbo\n(all OPENAI keys)"] -->|"All keys 429"| TRY4
    TRY4["Cross-provider: Try gemini-2.5-flash\n(all GEMINI keys)"] -->|"All keys 429"| TRY5
    TRY5["Try gemini-1.5-flash-latest\n...and so on"] -->|"All exhausted"| ERR

    TRY1 -->|"Success"| OK["Return response ✅"]
    TRY2 -->|"Success"| OK
    TRY3 -->|"Success"| OK
    TRY4 -->|"Success"| OK

    ERR["Raise: Critical — all models exhausted 🚨"]
```

### Key Rotation & Quota State

```mermaid
flowchart TD
    REQ["Request for model M with N keys"] --> FILTER

    FILTER["_available_keys_for(model, keys)
    Filter out sidelined keys:
    • key is in _quota_sidelined[model, key]
    • AND timestamp + 60s > now()"]

    FILTER --> KEYS_OK{"`Available
    keys exist?`"}
    KEYS_OK -->|"No"| RUNTIME_ERR["RuntimeError: All keys sidelined
    → Trigger model fallback"]
    KEYS_OK -->|"Yes"| TRY_EACH

    TRY_EACH["For each available key (in order):
    Try LLM call"]

    TRY_EACH --> RESP{"`Response
    type?`"}
    RESP -->|"Success"| RETURN["Return response ✅"]
    RESP -->|"429 / quota"| SIDELINE["_sideline_key(model, key)
    _quota_sidelined[(M, key)] = now()
    Try next key →"]
    RESP -->|"Other error"| RAISE["Re-raise exception"]

    SIDELINE --> TRY_EACH
```

---

## 🧬 Embedding Generator (`shared/embedding_generator.py`)

Used exclusively by the Knowledge Base seeder to vectorize documentation chunks for pgvector storage.

```mermaid
flowchart TD
    INPUT["text: str"] --> CHECK_KEYS

    CHECK_KEYS{"`OPENAI_API_KEYS
    configured?`"}
    CHECK_KEYS -->|"No"| ERR["RuntimeError: No OPENAI_API_KEYS"]
    CHECK_KEYS -->|"Yes"| SEMAPHORE

    SEMAPHORE["Acquire _embed_sem (Semaphore)
    EMBED_CONCURRENCY (default: 5)
    Prevents overwhelming OpenAI API"]

    SEMAPHORE --> POOL_LOOP

    POOL_LOOP["For each key in round-robin pool:
    POST https://api.openai.com/v1/embeddings
    {model: text-embedding-3-large,
     input: text,
     dimensions: 3072}"]

    POOL_LOOP --> RESP{"`Response?`"}
    RESP -->|"429 / quota"| NEXT_KEY["Try next key in pool →"]
    RESP -->|"API error"| RAISE_ERR["Raise RuntimeError"]
    RESP -->|"Success"| RETURN["Return data[0].embedding
    → List[float] (3072 dims)"]

    NEXT_KEY --> POOL_LOOP
    POOL_LOOP -->|"All keys tried"| FAIL["RuntimeError: All embedding keys failed"]
```

---

## ⚡ RAG Cache (`shared/rag_cache.py`)

Caches pgvector query results in Redis to avoid repeated expensive similarity searches for identical queries.

```mermaid
flowchart LR
    subgraph RAG_CACHE["rag_cache.py"]
        GET["get_cached_rag(query_hash)
        → Redis GET rag:v1:{hash}"]
        SET["set_cached_rag(query_hash, chunks)
        → Redis SETEX rag:v1:{hash} TTL=3600"]
        AVAIL["is_redis_available()
        Checks Redis connection on startup
        Falls back gracefully if Redis is down"]
    end

    CALLER["business_analyzer\nor semantic_validator"] -->|"hash(query_embedding)"| GET
    GET -->|"Miss"| PGVECTOR["pgvector search\n(kb_embeddings table)"]
    PGVECTOR -->|"results"| SET
    SET --> RETURN["Return chunks"]
    GET -->|"Hit"| RETURN
```

---

## 🗄️ Shared Database Layer (`shared/database/`)

```mermaid
graph TB
    subgraph DB["shared/database/db.py"]
        ASYNC_SESSION["AsyncSessionLocal\n(SQLAlchemy async)\nUsed by: Context Engine, CVS activities"]
        SYNC_SESSION["SessionLocal\n(SQLAlchemy sync)\nUsed by: Legacy activities, IS agents"]
        ENGINE["create_async_engine\n(asyncpg driver)\nDATABASE_URL from .env"]
    end

    subgraph MODELS["shared/models/"]
        CLIENT["Client\n→ clients table"]
        PROJECT["Project\n→ projects table\n(company_slug, f3iche, discovery_status)"]
        COMMAND["CommandWorkflowInput/Output\n→ OS workflow I/O dataclasses"]
        CVS_MODELS["ContextSnapshot\n→ context_snapshots table\nContextEvent\n→ cvs_context_events table"]
        IS_MODELS["ISSession, ISFile, ISProfile\nISTargetStructure, ISFieldMapping\nISMappedData, ISImportPlan\nISImportLog, ISAuditTrail"]
    end

    ASYNC_SESSION & SYNC_SESSION --> SUPABASE["Supabase PostgreSQL\n(hosted)"]
    DB --> MODELS
```

---

## ☁️ R2 Client (`shared/r2_client.py`)

```mermaid
graph LR
    subgraph R2_CLIENT["r2_client.py"]
        UPLOAD["upload_file(key, data, content_type)\n→ PUT to R2 bucket"]
        DOWNLOAD["download_file(key)\n→ GET from R2 bucket"]
        PRESIGN["get_presigned_url(key, expiry)\n→ Signed URL for frontend access"]
        LIST["list_objects(prefix)\n→ List files in a path prefix"]
        DELETE["delete_file(key)\n→ DEL from R2 bucket"]
    end

    subgraph PATHS["R2 Bucket Structure"]
        P1["clean-data/{slug}/{project_id}/
        ├── _manifest/
        │   └── manifest.json
        ├── _profile/
        │   └── company_context_v{N}.json
        ├── _target/
        │   └── target_structure.json
        ├── _validation/
        │   └── report.json
        ├── _import_plan/
        │   └── plan.json
        ├── mappings/
        │   └── {filename}.json
        └── {filename}.csv"]

        P2["quarantine/{slug}/{project_id}/
        └── {infected_filename}"]

        P3["cvs/{slug}/{project_id}/{layer}/
        └── v{N}.json"]
    end

    IS_WORKER["IS Worker"] --> UPLOAD & DOWNLOAD
    CVS_WORKER["CVS Worker"] --> UPLOAD
    FRONTEND["Frontend"] --> PRESIGN
```

---

## 🛡️ LLM Provider Abstraction (`shared/llm_providers/`)

Used by `invoke_agentic_loop` for tool-calling workflows:

```mermaid
graph TB
    subgraph PROVIDERS["shared/llm_providers/"]
        BASE["base.py\nBaseLLMProvider\n• invoke_agentic_loop(prompt, tools, schema)"]
        OPENAI_P["openai_provider.py\nOpenAIProvider\n• Uses OpenAI function calling API\n• Structured output via response_format"]
        GEMINI_P["gemini_provider.py\nGeminiProvider\n• Uses Gemini function declarations\n• Handles Part/Content response format"]
    end

    BASE --> OPENAI_P & GEMINI_P

    AGENTIC_LOOP["invoke_agentic_loop() in llm_router.py
    ─────────────────────────────────────────
    Selects provider based on model name
    Delegates tool-calling to provider
    Returns structured Pydantic model output"]

    AGENTIC_LOOP --> OPENAI_P & GEMINI_P
```

---

## 📊 Observability Stack

```mermaid
graph LR
    subgraph METRICS["Metric Sources"]
        OS_M["shared/os_metrics.py
        • os_commands_total (by status)
        • os_command_duration_seconds
        • os_llm_calls_total (by model)
        • os_ambiguity_rounds_total"]

        CVS_M["shared/cvs_metrics.py
        • cvs_snapshot_builds_total
        • cvs_snapshot_build_duration_seconds
        • cvs_webhooks_received_total"]

        CE_M["shared/context_engine/metrics.py
        • context_engine_requests_total
        • context_engine_latency_seconds
        • context_cache_hits_total"]
    end

    subgraph SCRAPE["Prometheus Scraping"]
        PROM["Prometheus :9090
        Scrapes /metrics from backend_api
        Rules: monitoring/prometheus/alerts-f3next.yml"]
    end

    subgraph VIZ["Visualization"]
        GRAFANA["Grafana :3001
        Dashboards: monitoring/grafana/dashboards/
        Provisioning: monitoring/grafana/provisioning/"]
    end

    OS_M & CVS_M & CE_M -->|"exposed via FastAPI /metrics"| PROM
    PROM --> GRAFANA
```

---

## 🔑 Environment Configuration (`.env`)

| Variable | Used By | Purpose |
|----------|---------|---------|
| `DATABASE_URL` | All workers, backend | Supabase PostgreSQL connection |
| `TEMPORAL_HOST` | All workers | Temporal server address |
| `REDIS_URL` | OS, CVS, IS, backend | Redis cache connection |
| `GEMINI_API_KEYS` | LLM router | Comma-separated Gemini API keys |
| `OPENAI_API_KEYS` | LLM router + embeddings | Comma-separated OpenAI API keys |
| `GEMINI_API_KEYS_COMPLEX` | LLM router | Premium keys for complex tasks |
| `OPENAI_EMBEDDING_MODEL` | Embedding generator | Model name (default: text-embedding-3-large) |
| `OPENAI_EMBED_DIMS` | Embedding generator | Output dimensions (default: 3072) |
| `R2_ACCOUNT_ID` | R2 client | Cloudflare R2 account |
| `R2_ACCESS_KEY_ID` | R2 client | R2 access key |
| `R2_SECRET_ACCESS_KEY` | R2 client | R2 secret |
| `R2_BUCKET_NAME` | R2 client | R2 bucket name |
| `SUPABASE_URL` | Frontend | Supabase project URL |
| `SUPABASE_ANON_KEY` | Frontend | Supabase anonymous key |
| `GEMINI_MODEL_TIERS` | LLM router | Override Gemini model fallback order |
| `OPENAI_MODEL_TIERS` | LLM router | Override OpenAI model fallback order |
