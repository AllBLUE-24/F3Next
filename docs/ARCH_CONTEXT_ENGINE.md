# Context Engine — Architecture & Flow

> The Context Engine is the **shared intelligence layer** that assembles complete company context for every OS command. It merges static ERP schema knowledge, industry-specific templates, and live CVS snapshots into a single `ProjectContext` object — with a tiered Redis + in-process cache to keep latency sub-50ms.

### Live Entity Registry (LER) overlay — v1.0.0 foundation

**CVS may suggest; LER decides.** Context snapshots and OS commands also carry a **live ERP overlay** built by `shared/entity_resolution/` (`build_link_cache`, `resolve_entities_batch`). This wraps `BulkLinkResolver` — the same path IS import preflight uses — so validators and planners check **live Frappe link names**, not stale CVS alone. Keys: `link_cache`, `resolved_entities`, `resolution_gaps`, `live_fetched_at`, `brain_version`. Wired into workflows on `foundation/os-brain`; see [`docs/v1.0.0/branch-02-foundation-os-brain.md`](v1.0.0/branch-02-foundation-os-brain.md).

---

## 🏗️ Component Map

```
shared/context_engine/
├── __init__.py         ← Exports ContextEngine, get_context_engine()
├── engine.py           ← ContextEngine class — main orchestrator
├── loader.py           ← Tier1Loader, load_tier2_f3iche, retrieve_kb_chunks
├── cache.py            ← ContextCache (Redis-backed, in-process L1)
├── versioning.py       ← Cache key generation (context_cache_key, tier2_cache_key)
├── models.py           ← ProjectContext dataclass
├── config.py           ← Config (TTLs, Redis URL)
└── metrics.py          ← Prometheus: CONTEXT_ENGINE_LATENCY, CONTEXT_ENGINE_REQUESTS
```

---

## 🏛️ 3-Tier Architecture

```mermaid
graph TB
    subgraph CALLER["OS Agent / IS Agent"]
        ACT["retrieve_context\nactivity.py"]
    end

    subgraph ENGINE["ContextEngine.get_context()"]
        CACHE_CHECK{"L1/L2 Cache\nHit?"}
        T1["Tier 1 — Static ERP Schema
        ─────────────────────────────────
        Tier1Loader (in-process, file-based)
        • ERPNext doctype graph
        • Field definitions per doctype
        • Required fields, child tables
        • Valid link targets
        Loaded once, checksum-verified"]

        T2["Tier 2 — F3iche Industry Templates
        ─────────────────────────────────────
        load_tier2_f3iche(f3iche_id)
        Reads from Supabase: f3iche_templates
        • Industry-specific doctype overrides
        • Default field values for the F3iche
        • Business logic rules
        Cached in Redis (tier2:v1:{f3iche_id}:)"]

        CVS["Tier 3 — Live CVS Snapshots
        ─────────────────────────────────
        Reads context_snapshots table (Supabase)
        For each layer (identity, master_data):
          SELECT * WHERE project_id = ?
          ORDER BY version DESC LIMIT 1
        → known_customers[]
        → known_items[]
        → known_suppliers[]
        → warehouses[]
        → company_profile"]

        MERGE["Merge all 3 tiers
        apply_f3iche_to_graph()
        Build ProjectContext"]
    end

    subgraph KB["Tier 3 — Knowledge Base (on-demand)"]
        KB_SEARCH["retrieve_kb_chunks()
        pgvector similarity search
        APQC + ERPNext docs + F3iche knowledge
        Called explicitly by: business_analyzer,
        semantic_validator, industry knowledge step"]
    end

    ACT --> CACHE_CHECK
    CACHE_CHECK -->|"Miss"| T1 & T2 & CVS
    T1 & T2 & CVS --> MERGE
    MERGE -->|"Write to cache"| REDIS["Redis\n(ctx:v1:{project_id}:{f3iche_id}:{layers}:{version})"]
    CACHE_CHECK -->|"Hit"| RETURN["Return ProjectContext\n(from cache)"]
    MERGE --> RETURN
    ACT -->|"get_tier3_chunks()"| KB_SEARCH
    KB_SEARCH --> REDIS2["Redis\n(RAG query cache)"]
```

---

## 🔁 get_context() Execution Flow

```mermaid
flowchart TD
    START["ContextEngine.get_context(
    project_id, f3iche_id,
    layers=['identity','master_data'],
    version=None, include_tier3=False)"] --> CACHE_KEY

    CACHE_KEY["Build cache key:
    context_cache_key(project_id, f3iche_id, layers, version)
    → 'ctx:v1:{proj}:{f3iche}:{layers_hash}:{version}'"]

    CACHE_KEY --> L1_CHECK{"`L1/L2 cache
    hit?`"}

    L1_CHECK -->|"Hit"| CACHE_RETURN["observe_cache_hit('l1_or_l2')
    Increment CONTEXT_ENGINE_REQUESTS (cache_hit)
    Record CONTEXT_ENGINE_LATENCY
    Return ProjectContext(**cached)"]

    L1_CHECK -->|"Miss"| TIER1

    TIER1["Tier1Loader.load()
    ──────────────────────────
    Reads static ERPNext schema files
    (bundled with the worker container)
    Returns: tier1_bundle, checksum
    ⚡ In-process — no I/O after first load"]

    TIER1 --> T2_CACHE{"`tier2 cache
    hit?`"}

    T2_CACHE -->|"Hit"| T2_USE["Use cached tier2
    observe_cache_hit('tier2_subcache')"]

    T2_CACHE -->|"Miss"| T2_LOAD["load_tier2_f3iche(f3iche_id)
    ─────────────────────────────────
    SELECT * FROM f3iche_templates
    WHERE f3iche_id = ?
    Returns: field overrides, business rules"]

    T2_USE & T2_LOAD --> MERGE_GRAPH["apply_f3iche_to_graph(graph_doc, tier2)
    ──────────────────────────────────────
    Overlays F3iche-specific rules onto
    the base ERPNext doctype graph"]

    MERGE_GRAPH --> CVS_LOAD["Load CVS Layers from Supabase
    ──────────────────────────────────────
    Try to resolve project_id:
    • If UUID → use directly
    • If slug → SELECT id FROM projects WHERE company_slug = slug
    ──────────────────────────────────────
    For each layer in layers[]:
      SELECT * FROM context_snapshots
      WHERE project_id = ? AND layer = ?
      ORDER BY version DESC LIMIT 1
      → cvs_data[layer] = row.data"]

    CVS_LOAD -->|"Exception (ERP offline / no CVS yet)"| CVS_WARN["logger.warning
    Continue with cvs_data = {}
    (OS agent handles gracefully)"]

    CVS_LOAD --> BUILD_PC["Build ProjectContext:
    ────────────────────────
    project_id, f3iche_id, layers,
    tier1=tier1_bundle,
    tier2_raw=tier2,
    tier2_merged_graph=merged_graph,
    cvs=cvs_data,
    tier1_checksum=checksum"]

    CVS_WARN --> BUILD_PC

    BUILD_PC --> WRITE_CACHE["Write to cache:
    await cache.set(key, payload)"]

    WRITE_CACHE --> METRICS["Increment CONTEXT_ENGINE_REQUESTS (miss)
    Record CONTEXT_ENGINE_LATENCY"]

    METRICS --> RETURN_PC["Return ProjectContext"]
```

---

## 🗃️ Cache Architecture

```mermaid
graph LR
    subgraph CACHE["ContextCache"]
        L1["L1: In-process dict\n(Python process memory)\nZero-latency\nLost on restart"]
        L2["L2: Redis\nPersistent across restarts\nShared across all workers\n~1ms latency"]
    end

    subgraph KEYS["Cache Key Namespaces"]
        K1["ctx:v1:{project_id}:{f3iche_id}:{layers}:{version}\n→ Full ProjectContext"]
        K2["tier2:v1:{f3iche_id}:{version}\n→ F3iche template data"]
        K3["rag:v1:{query_hash}\n→ KB chunk results (rag_cache.py)"]
    end

    subgraph INVALIDATION["Cache Invalidation"]
        INV1["CVS Step 3: invalidate_session_cache\n→ DEL ctx:v1:{project_id}:*\n→ DEL os_session:{session_id}:*"]
        INV2["ContextEngine.invalidate_project(project_id)\n→ cache.invalidate_prefix(f'ctx:v1:{project_id}:')"]
        INV3["ContextEngine.invalidate_f3iche(f3iche_id)\n→ cache.invalidate_prefix(f'tier2:v1:{f3iche_id}:')"]
    end

    L1 --> L2
    KEYS --> CACHE
    INVALIDATION --> CACHE
```

---

## 📐 ProjectContext Model

```python
@dataclass
class ProjectContext:
    project_id: str
    f3iche_id: str
    layers: list[str]

    # Tier 1 — Static ERP schema
    tier1: dict              # {doctype_graph: {...}, field_defs: {...}}
    tier1_checksum: str      # SHA256 of tier1 bundle (for cache invalidation)

    # Tier 2 — Industry template
    tier2_raw: dict          # Raw F3iche template from Supabase
    tier2_merged_graph: dict # tier1 graph + tier2 overlays merged

    # Tier 3 — Live company data (from CVS)
    cvs: dict[str, Any]      # {identity: {...}, master_data: {...}}
    # cvs['master_data'] contains:
    #   known_customers: [{name, customer_name, customer_group}, ...]
    #   known_items: [{item_code, item_name, stock_uom, item_group}, ...]
    #   known_suppliers: [{name, supplier_name, supplier_group}, ...]
    #   warehouses: [{name, is_group}, ...]

    context_version: Optional[int]  # Pinned version (for audit replay)
```

---

## 🔍 Tier 3 On-Demand: Knowledge Base Chunks

The `get_tier3_chunks()` method performs **semantic search** over the knowledge base — used by the Business Analyzer and Semantic Validator:

```mermaid
flowchart LR
    CALLER["business_analyzer.py\nor semantic_validator.py"] -->|"query text"| EMBED

    EMBED["generate_embedding(query_text)
    OpenAI text-embedding-3-large
    → 3072-dim vector"] --> CACHE_CHECK

    CACHE_CHECK{"`RAG cache
    hit? (Redis)`"}
    CACHE_CHECK -->|"Hit"| RETURN_CACHE["Return cached chunks
    (rag_cache.py TTL: 1 hour)"]
    CACHE_CHECK -->|"Miss"| PGVECTOR

    PGVECTOR["pgvector cosine similarity search
    SELECT content, source, score
    FROM kb_embeddings
    ORDER BY embedding <=> $query_vec
    LIMIT top_k (default: 5)
    WHERE source LIKE kb_source_prefix%"]

    PGVECTOR --> CACHE_WRITE["Write to Redis RAG cache"]
    CACHE_WRITE --> RETURN["Return: list[str] (chunk texts)"]
    RETURN_CACHE --> RETURN
```

---

## 📊 Knowledge Base Contents

```mermaid
graph TB
    subgraph KB["kb_embeddings (pgvector)"]
        APQC["APQC Process Classification Framework
        Source: seed_apqc.py
        Content: Business process definitions,
        industry cross-references
        ~2,000+ chunks"]

        ERPNEXT_DOCS["ERPNext Documentation
        Source: seed_erpnext_docs.py
        Content: DocType descriptions, field guides,
        workflow explanations, business rules
        ~5,000+ chunks"]

        F3ICHE["F3iche Domain Knowledge
        Source: seed_f3iches.py
        Content: Industry-specific ERP guidance,
        manufacturing/trading/services best practices
        ~500+ chunks"]
    end

    APQC & ERPNEXT_DOCS & F3ICHE -->|"OpenAI text-embedding-3-large\nvector(3072)"| VECTOR_COL["embedding vector(3072)"]
```

---

## 🔑 Key Design Decisions

1. **Tiered cache = speed** — L1 (in-process dict) catches repeated requests within the same worker process. L2 (Redis) catches requests across workers and restarts. Cache miss only hits Supabase.

2. **CVS failure is non-fatal** — If Supabase is unreachable or there's no CVS snapshot yet, `get_context()` logs a warning and continues with `cvs = {}`. The OS agent's readiness blocker will catch the missing data case.

3. **Checksum-based Tier 1 invalidation** — The static ERP schema (Tier 1) is bundled with the worker container and loaded once. If the schema file changes, the checksum changes, and all cached context entries become invalid.

4. **Slug → UUID resolution** — Context can be requested by either the project UUID or the human-readable `company_slug`. The engine resolves slugs to UUIDs transparently via a single DB lookup.
