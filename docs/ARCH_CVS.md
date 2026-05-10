# Context Versioning Service (CVS) — Architecture & Flow

> The CVS is F3Next's **event-driven context synchronization layer**. It continuously keeps a structured snapshot of each company's live ERPNext data (customers, suppliers, items, warehouses) in Supabase, so the OS Agent always has fresh, accurate context without making expensive real-time API calls during command execution.

---

## 🏗️ Component Map

```
containers/context_versioning/
├── cvs_worker.py                  ← Main worker — cvs-main-queue
├── poller_worker.py               ← Cron poller — periodic sync trigger
├── recovery_worker.py             ← Stuck event recovery
├── cvs_workflow/
│   └── workflow.py                ← CVSUpdateWorkflow (4-step, ~7KB)
├── snapshot_builder/
│   └── activities.py              ← build_and_store_snapshot (ERPNext → Supabase + R2)
└── context_store/
    └── activities.py              ← read_latest_snapshot, invalidate_session_cache,
                                     log_context_event, mark_event_processed,
                                     register_frappe_webhooks, recover_stuck_events,
                                     cvs_force_sync_for_project

shared/
├── cvs_profile.py                 ← CVS profile utilities
├── cvs_metrics.py                 ← Prometheus metrics for CVS
└── cvs_routing.py                 ← Routing helpers for CVS workflow IDs
```

---

## 🔄 Trigger Architecture (3 Entry Points)

```mermaid
graph TD
    subgraph TRIGGERS["CVS Trigger Sources"]
        T1["1. IS Pipeline\n(Step 13.5)\nPOST /api/cvs/force-sync/{company_id}\nAfter deployment is complete"]
        T2["2. ERPNext Webhook\nFrappe → POST /api/cvs/webhook/{company_id}\nWhen master data changes in ERPNext"]
        T3["3. OS Command Success\nAfter a successful OS write operation\ncvs-os-{project_id}-{command_id}"]
        T4["4. Poller / Cron\nperiodic force-sync for all companies\n(fallback when webhooks miss events)"]
        T5["5. Manual Force-Sync\nAdmin API call\ncvs-force-{project_id}"]
    end

    subgraph WORKFLOW_IDS["Temporal Workflow IDs (dedup strategy)"]
        WID1["cvs-force-{project_id}\n(replaces any running sync)"]
        WID2["cvs-wh-{project_id}-{doc_name}\n(one per webhook event)"]
        WID3["cvs-os-{project_id}-{command_id}\n(one per OS success)"]
    end

    T1 & T4 & T5 --> WID1
    T2 --> WID2
    T3 --> WID3

    WID1 & WID2 & WID3 --> CVS_WF["CVSUpdateWorkflow\n(cvs-main-queue)"]
```

---

## 🔁 CVSUpdateWorkflow — 4-Step Pipeline

```mermaid
flowchart TD
    START(["`**START**
    CVSUpdateInput:
    {project_id, company_slug,
    company_profile, trigger_event,
    layers[], trigger_doctype}`"]) --> S1

    S1["**STEP 1 — Log Context Event**
    log_context_event
    ───────────────────────────────
    Creates audit record in Supabase:
    • cvs_context_events table
    • event_type, event_payload, doctype
    • workflow_id (for traceability)
    Returns: event_id"]

    S1 --> S2

    S2["**STEP 2 — Build & Store Snapshot**
    build_and_store_snapshot
    ───────────────────────────────────────────────────
    Fetches fresh data from ERPNext REST API for
    each layer in layers[]:
    ─────────────────────────────────────────────────
    Layer: identity
      → Company details, ERP version, modules enabled
    Layer: master_data
      → Customers (names, IDs, groups)
      → Suppliers (names, IDs, groups)
      → Items (codes, names, UOM, item groups)
      → Warehouses (names, is_group)
      → Price Lists
    ─────────────────────────────────────────────────
    Writes to Supabase: context_snapshots table
      • project_id, layer, version (auto-increment)
      • data (JSONB blob)
      • trigger_event, trigger_doctype
    Writes to R2: cvs/{slug}/{project_id}/{layer}/v{N}.json
    ─────────────────────────────────────────────────
    Retry: 3 attempts, 5s backoff
    Timeout: 120s (ERPNext can be slow)"]

    S2 --> S2_OK{"`snapshot_result
    .success?`"}
    S2_OK -->|"No"| FAIL(["Return: success=False\nerror=Snapshot build failed"])
    S2_OK -->|"Yes"| S2B

    S2B["**STEP 2b — Mark Event Processed**
    mark_event_processed
    ───────────────────────────────────
    Updates cvs_context_events:
    • status = processed
    • processed_version = max_version"]

    S2B --> S3

    S3["**STEP 3 — Invalidate OS Session Caches**
    invalidate_session_cache
    ─────────────────────────────────────────────
    Clears Redis keys:
    • ctx:v1:{project_id}:*
      (Context Engine Tier-3 / CVS layer cache)
    • os_session:{session_id}:*
      (OS worker session context cache)
    Ensures next OS command picks up fresh data
    Returns: sessions_cleared count"]

    S3 --> DONE(["`**DONE**
    CVSUpdateOutput:
    {success=True, versions{},
    r2_keys{}, layers_built[]}`"])

    FAIL --> END(["Return error output"])
```

---

## 🗃️ Snapshot Layer Architecture

```mermaid
graph TB
    subgraph SNAPSHOT["context_snapshots Table (Supabase)"]
        ROW1["Row: layer=identity, version=3
        data: {company_name, erp_version, modules[]}"]
        ROW2["Row: layer=master_data, version=7
        data: {customers[], suppliers[], items[],
               warehouses[], price_lists[]}"]
    end

    subgraph ENGINE["Context Engine reads"]
        CE["ContextEngine.get_context()
        Queries latest version per layer
        ORDER BY version DESC LIMIT 1"]
    end

    subgraph OS["OS Agent reads"]
        OS_ACT["retrieve_context activity
        Calls ContextEngine → reads CVS layer
        Injects into command pipeline as:
        context.company_profile
        context.entity_registry.known_customers[]
        context.entity_registry.known_items[]
        context.entity_registry.known_suppliers[]"]
    end

    ROW1 & ROW2 --> CE
    CE --> OS_ACT
```

---

## 🔁 Worker Fleet

```mermaid
graph LR
    subgraph CVS_WORKERS["CVS Worker Fleet (3 processes)"]
        W1["cvs_worker
        Main workflow runner
        cvs-main-queue
        All activities + CVSUpdateWorkflow"]

        W2["cvs_poller
        Periodic sync trigger
        Reads all active projects
        Triggers force-sync for each"]

        W3["cvs_recovery
        Stuck event recovery
        Queries cvs_context_events
        where status=pending AND age > threshold
        Re-triggers those sync workflows"]
    end

    Temporal["Temporal Server\n:7233"] --> W1 & W2 & W3
    W2 -->|"start_workflow per project"| Temporal
    W3 -->|"start_workflow for stuck events"| Temporal
```

---

## 📡 Frappe Webhook Integration

```mermaid
sequenceDiagram
    participant ERPNext as Customer ERPNext
    participant API as FastAPI
    participant T as Temporal
    participant CVS as CVS Worker

    Note over ERPNext: User creates/updates Customer in ERPNext

    ERPNext->>API: POST /api/cvs/webhook/{company_id}
    Note right of API: Frappe sends:
    note: {doctype, docname, event_type}

    API->>API: Validate webhook_secret header

    API->>T: start_workflow(CVSUpdateWorkflow,
    note: workflow_id="cvs-wh-{proj}-{docname}")

    T->>CVS: Execute pipeline
    CVS->>ERPNext: Fetch fresh master_data
    CVS->>Supabase: Write new context_snapshot v{N+1}
    CVS->>Redis: Invalidate OS session caches

    Note over CVS: Next OS command gets fresh context
```

---

## 📊 Prometheus Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `cvs_snapshot_builds_total` | Counter | Total snapshot builds (success/failure) |
| `cvs_snapshot_build_duration_seconds` | Histogram | Time to build a snapshot |
| `cvs_webhooks_received_total` | Counter | Webhook events received |
| `cvs_cache_invalidations_total` | Counter | Redis cache invalidations |
| `cvs_context_event_age_seconds` | Gauge | Age of pending unprocessed events |

---

## 🗄️ Database Tables

| Table | Owner | Contents |
|-------|-------|---------|
| `context_snapshots` | CVS | Latest per-layer snapshots (versioned JSONB) |
| `cvs_context_events` | CVS | Audit log of every sync trigger event |

---

## ⚙️ Workflow ID Strategy (Deduplication)

The CVS uses Temporal's workflow ID uniqueness to prevent redundant syncs:

```
force_sync:  cvs-force-{project_id}
  → If a force-sync is already running, the new one terminates the old one
  → Ensures only ONE sync runs per company at a time

webhook:     cvs-wh-{project_id}-{doc_name}
  → One workflow per ERPNext document change event
  → Multiple events for different documents run in parallel

os_command:  cvs-os-{project_id}-{command_id}
  → One refresh per successful OS command
  → Lightweight: only refreshes affected layer
```
