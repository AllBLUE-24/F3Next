# F3Next V2 — Architecture Vision

> **Status:** Planning — not yet implemented  
> **Branch:** `feature/v2-architecture` (to be created)  
> **Author:** Architecture Review, May 2026  
> **Context:** This document supersedes the current V1 pipeline architecture described in `ARCH_IMPLEMENTATION.md`. V1 remains in production until V2 is proven. This is a forward-looking design, not a migration instruction.

---

## The Problem with V1

V1 works — but it works for **specific definitions only**. It is tightly coupled to:

- ERPNext as the only real ERP (other adapters exist but schema knowledge is ERPNext-specific)
- Green Surface / manufacturing as the primary tested use case
- A fixed set of doctypes whose synonyms someone hand-wrote in a JSON file
- A deterministic Python pipeline that breaks when reality doesn't match its hardcoded assumptions

The core symptom: **adding BOM support required editing a JSON file and fixing three code functions**. In a truly scalable system, adding BOM support should require nothing — the system should figure it out by reading the live ERP.

---

## V2 Goals

| Goal | What it means |
|------|---------------|
| **Any natural language input works** | "Here are my files" or "set up my company" — the system reasons from intent, not from keyword matching |
| **Any industry works** | Construction, pharma, retail, manufacturing — no code changes, just load the right F3iche playbook |
| **Any ERP works** | ERPNext, Odoo, SAP B1, Dynamics — register an adapter + connect an instance, nothing else |
| **Any file format works** | CSV, XLSX, messy TXT, PDF, WhatsApp exports — the system parses and reasons |
| **Scalable by data, not by code** | Adding a new ERP, industry, or doctype = adding data (a row, a document, an API registration). Never a code change |
| **Industry standard** | Tool calling, agentic reasoning, live schema introspection — not synonym lists in JSON |
| **CLI / MCP accessible** | Other agents (Cursor, Claude, custom scripts) can call F3Next programmatically |

---

## Core Design Principle: The Reasoning Agent

**V1 approach:**
```
User CSV → Python deterministic matching → hardcoded JSON synonyms → ERP field
```

**V2 approach:**
```
User CSV → Agent calls tools → gets live schema → reasons → ERP field
```

The shift is from **pre-programming intelligence into code** to **giving an agent the tools to discover intelligence at runtime**. This is exactly how coding agents (Cursor, Claude Code, Devin) work — they don't have a hardcoded map of every Python library. They read the file, run the code, and reason about it.

**The V2 agent has three things coding agents have that V1 lacked:**
1. **Tools** — callable functions that return real data on demand
2. **Reasoning** — LLM that interprets results and makes decisions
3. **Feedback loops** — if a step fails, the agent tries a different approach

---

## System Architecture — High-Level Node View

```
┌─────────────────────────────────────────────────────────────────────┐
│                        F3Next V2 Engine                             │
│                                                                     │
│  INPUT (any format, any language, any ERP target)                   │
│       │                                                             │
│       ▼                                                             │
│  ┌─────────┐    ┌──────────┐    ┌─────────┐    ┌─────────────┐     │
│  │  PARSE  │───▶│ CLASSIFY │───▶│  PLAN   │───▶│  MAP (LLM)  │     │
│  └─────────┘    └──────────┘    └─────────┘    └─────────────┘     │
│                                                        │            │
│                                                        ▼            │
│                               ┌──────────────────────────────┐      │
│                               │  VALIDATE → IMPORT → VERIFY  │      │
│                               └──────────────────────────────┘      │
│                                                                     │
│  FEEDING LAYER (always available to every node via tools)           │
│  ┌─────────────────┐  ┌──────────────────┐  ┌──────────────────┐   │
│  │  Live Schema    │  │  Semantic Context │  │  Business Graph  │   │
│  │  (REST API)     │  │  (pgvector RAG)   │  │  (DB table)      │   │
│  │  Redis cached   │  │                  │  │                  │   │
│  └─────────────────┘  └──────────────────┘  └──────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

Every node in the pipeline is:
- **Stateless** — takes an input, returns an output, no hidden state
- **Tool-equipped** — can call any feeding layer on demand
- **Retryable** — if it fails, Temporal retries it cleanly
- **ERP-agnostic** — never contains the word "ERPNext" in core logic

---

## The Three Feeding Layers

This is the heart of V2. Instead of one monolithic `field_mappings.json` doing three jobs at once, V2 has **three distinct feeding layers** — each with a clear job, a clear owner, and a clear access method.

---

### Layer 1 — Live Schema Feed (REST API → Redis)

**Job:** Answer the question *"What does the ERP expect?"*

**What it contains:**
- Field names and their data types (`fieldtype`)
- Which fields are mandatory (`reqd`)
- What a Link field points to (`options`)
- What child tables exist and their own field lists
- Custom fields added by the client

**How it works:**
```
Agent needs schema for "BOM"
  → Check Redis cache (key: {erp_type}:{instance_id}:schema:BOM)
  → Cache miss? Call ERPAdapter.get_doctype_schema("BOM")
  → ERPAdapter calls live ERP REST API
  → Store in Redis (TTL: 24h for standard, 1h for client-custom)
  → Return structured field list
```

**Why not JSON files?**
- JSON files go stale with ERP version updates
- JSON files can't know about client-specific custom fields
- JSON files require a developer to maintain them
- Live API always returns exactly what the running ERP instance expects

**ERP agnostic contract — every adapter implements:**
```python
async def get_doctype_schema(doctype: str) -> list[FieldDefinition]:
    """Returns [{fieldname, fieldtype, mandatory, options, default}]"""

async def list_doctypes() -> list[str]:
    """Returns all doctype names available in this ERP"""

async def get_child_doctypes(doctype: str) -> dict[str, list[FieldDefinition]]:
    """Returns {table_fieldname: [child_field_definitions]}"""
```

**What this replaces from V1:** The schema-fact portions of `field_mappings.json` and `erpnext_doctype_graph.json`

---

### Layer 2 — Semantic Context Feed (pgvector RAG)

**Job:** Answer the question *"What does this business context mean?"*

**What it contains:**
- **F3iche playbooks** — industry-specific implementation knowledge (manufacturing, trading, construction, pharma, etc.)
- **APQC process frameworks** — industry process models
- **ERP module docs** — what each module does, when to use it, common pitfalls
- **Business vocabulary** — industry-specific terms, common naming conventions, how different industries call the same thing
- **Default value reasoning** — why a manufacturing SME defaults `item_group` to "Raw Material", why a services company doesn't need warehouses
- **Implementation sequencing knowledge** — why you create Company before Warehouse, why BOM needs Item first

**How it works:**
```
Agent reasoning about a file named "fg_primer_bom_recipes.csv"
  → Embed query: "bill of materials manufacturing recipe file classification"
  → pgvector similarity search across {f3iche, erpnext_docs, apqc}
  → Returns: top-5 relevant chunks with manufacturing BOM context
  → Agent uses this to reason about the file's purpose
```

**Why this beats synonym lists:**
Synonyms are brittle — they only match what someone thought of in advance. Semantic search finds relevant context even for terminology the developer never anticipated. A Turkish user calling their BOM a "reçete" (Turkish for recipe) would find no synonym match but would score high on semantic similarity to "recipe" and "bill of materials".

**What this replaces from V1:** The `doctype_classifier_hints`, industry-specific knowledge in `f3iches/*.json`, documentation in `erpnext_docs pgvector` collection (already there), and the synonym matching approach entirely

---

### Layer 3 — Business Graph Feed (DB table, not JSON)

**Job:** Answer the question *"In what order do things need to happen?"*

**What it contains:**
- Doctype dependency ordering — "Item Group must exist before Item, Item before BOM, BOM before Work Order"
- Implementation phase sequencing — Phase A (config), Phase B (masters), Phase C (transactions)
- Safe default values for each doctype in each industry context (kept here because no API returns these — they are F3Next's curated product knowledge)

**Why this must stay in F3Next (not live API):**
No ERP API will ever tell you *"for a manufacturing SME, set item_group to Raw Material as a safe default"* or *"always create Warehouse before Item"*. This is F3Next's domain intelligence — the thing that makes the system smart rather than generic. But it should live in a **database table**, not a JSON file, so it can be updated without code deployments.

```sql
-- V2 schema
CREATE TABLE erp_setup_graph (
    id          UUID PRIMARY KEY,
    erp_type    TEXT NOT NULL,           -- 'erpnext', 'odoo', 'sap_b1'
    doctype     TEXT NOT NULL,
    layer       INT NOT NULL,            -- 0=system, 1=config, 2=masters...
    depends_on  TEXT[],                  -- must exist before this
    phase       TEXT NOT NULL,           -- 'phase_a_config', 'phase_b_master'...
    sme_relevance TEXT,                  -- 'always', 'conditional', 'never'
);

CREATE TABLE erp_safe_defaults (
    id          UUID PRIMARY KEY,
    erp_type    TEXT NOT NULL,
    f3iche_id   TEXT,                   -- null = applies to all industries
    doctype     TEXT NOT NULL,
    fieldname   TEXT NOT NULL,
    default_value TEXT NOT NULL,
    reasoning   TEXT,                   -- why this is the safe default
);
```

**What this replaces from V1:** `erpnext_doctype_graph.json` and `erpnext_deafaults_baseline.json` — same data, now queryable, updatable, and versionable without touching code.

---

## ERP Agnostic Design

**V1 problem:** Adding Odoo support requires modifying dozens of Python files, knowing which JSON files to update, and testing everything.

**V2 solution:** Adding Odoo support requires:
1. Implementing `OdooAdapter(ERPAdapter)` — ~200 lines of code, one file
2. Registering it in `erp_registry` table (one row)
3. Connecting a reference Odoo instance (one config entry)
4. Optionally seeding the `erp_setup_graph` table with Odoo's dependency order

**Nothing in the core engine changes.** The pipeline nodes don't know what ERP they're talking to — they only know they can call `get_doctype_schema(doctype)` and get a standardized response.

```python
# The ERP Registry — the only ERP-specific config the system reads
class ERPRegistry:
    erp_type: str                  # "erpnext" | "odoo" | "sap_b1"
    adapter_class: str             # "ERPNextAdapter"
    reference_instance_url: str    # "https://demo.erpnext.com"
    reference_api_key: str         # for schema introspection pre-deployment
    schema_cache_ttl_hours: int    # 24 for standard, 1 for client-custom
```

---

## Industry Agnostic Design

**V1 problem:** Adding a new industry (e.g., pharma with batch tracking and quality inspection) requires writing new Python classifiers and updating multiple files.

**V2 solution:** Adding pharma support requires:
1. Writing a `pharma.json` F3iche playbook (structured document with industry context, typical doctypes, process flows, vocabulary)
2. Seeding it into pgvector — one CLI command
3. Adding pharma-specific rows to `erp_safe_defaults` and `erp_setup_graph`

The discovery agent reads the playbook. The mapping agent retrieves it. The import agent uses its sequencing. No Python changes.

---

## Node Definitions

### Node 1 — PARSE
**Input:** Raw file(s) from R2 (CSV, XLSX, TXT, PDF)  
**Job:** Convert to clean tabular or text representation  
**Output:** `{filename, columns[], rows[], content_type, encoding}`  
**Tools called:** None (pure computation)  
**V2 change from V1:** Unchanged — this is already clean

---

### Node 2 — CLASSIFY
**Input:** Parsed file representation  
**Job:** Determine which ERP doctype this file represents  
**Output:** `{doctype, confidence, reasoning}`

**V2 implementation:**
```
1. Call get_candidate_doctypes() → from session ISTargetStructure
2. For each candidate, call get_doctype_schema(candidate) → Layer 1
3. Semantic search: file columns + filename → Layer 2 (F3iche, module docs)
4. LLM reasons: "Given these columns and this context, which doctype fits best?"
5. LLM returns structured output: {doctype, confidence, reasoning}
```

**Why this beats V1:** The LLM sees actual field definitions, actual industry context, and reasons. No synonym list. No hardcoded priors. A column called `receta_item` (Spanish for recipe item) still maps correctly because the LLM reasons semantically.

---

### Node 3 — PLAN
**Input:** Classified files + company profile + F3iche  
**Job:** Determine what to create, in what order, across which phases  
**Output:** `ISImportPlan` — phased, sequenced, dependency-aware

**V2 implementation:**
```
1. Query erp_setup_graph table for all required doctypes → Layer 3
2. Semantic search: F3iche + industry playbook → Layer 2
3. LLM reasons: "Given these doctypes and this company type, what's the safest import order?"
4. Human-in-the-loop gate: user confirms or adjusts the plan
```

**V2 change from V1:** Graph query moves from file-read to DB query. Planning LLM gets richer context from semantic search, not just a JSON dump.

---

### Node 4 — MAP (The Biggest Change)
**Input:** Parsed file rows + classified doctype + import plan  
**Job:** Map every CSV column to an ERP field. Normalize values. Build child table structure.  
**Output:** `{doctype, records[], link_fields{}}`

**V2 implementation — fully agentic:**
```
1. Call get_doctype_schema(doctype) → Layer 1 (live schema, full field list + child tables)
2. Semantic search: "mapping {doctype} {columns} {industry}" → Layer 2 (examples, patterns)
3. Query erp_safe_defaults for this doctype + f3iche → Layer 3 (safe default values)
4. LLM receives:
     - CSV columns and sample rows
     - Full live ERP schema (field names, types, mandatory, options)
     - Relevant industry context from RAG
     - Safe defaults for missing mandatory fields
5. LLM produces:
     - Column → field mapping (no synonym list needed)
     - Child table structure (items[], timesheet_detail[], etc.)
     - Injected defaults for missing mandatory fields
     - Confidence and reasoning for each mapping decision
```

**No more:** `user_input_synonyms`, `fold_child_tables` heuristics, `apply_defaults_and_normalize` hardcoding. The LLM does all of this guided by live schema + context.

---

### Node 5 — VALIDATE
**Input:** Mapped records + live schema  
**Job:** Verify every record satisfies ERP constraints before import  
**Output:** `{valid_records[], invalid_records[], issues[]}`

**V2 implementation:**
```
1. For each record: call get_doctype_schema() → verify mandatory fields present
2. For Link fields: call get_linked_record(doctype, value) → verify referenced record exists
3. For Select fields: call get_field_options(doctype, fieldname) → verify value is allowed
4. Child table validation: verify minimum_rows constraints
5. LLM step (optional): for complex business rule violations, explain to user in plain language
```

**V2 change from V1:** Validation uses live schema exclusively — not `_REQUIRED_FIELDS_FALLBACK` dicts or `validation_rules.json`. A live ERP instance is the only authoritative source of truth for what it will accept.

---

### Node 6 — IMPORT
**Input:** Validated records + import plan + ERP adapter  
**Job:** Execute phased import — config first, masters next, transactions last  
**Output:** `{imported[], failed[], warnings[]}`

**V2 implementation:** Largely unchanged from V1. The adapter interface is already well-designed. V2 improves error handling:
```
On failure:
  → Retry with exponential backoff (Temporal handles this)
  → If still failing: call get_doctype_schema() to re-validate
  → If schema mismatch: flag for human review with LLM-generated explanation
```

---

### Node 7 — VERIFY
**New in V2:** After import, the agent verifies by reading back what it wrote.
```
For each imported doctype:
  → Call adapter.list_records(doctype, filters={imported_ids})
  → Compare against expected records
  → Report discrepancies with LLM-generated explanation
```

This is the feedback loop that makes the system self-correcting — just like a coding agent runs tests after making changes.

---

## The CLI / MCP Layer

**Goal:** F3Next should be callable by other agents — Cursor, Claude, custom enterprise scripts — not just by the web UI.

### F3Next CLI
```bash
# Run a full implementation session from terminal
f3next implement \
  --project green-surface \
  --files ./data/*.csv \
  --erp erpnext \
  --industry manufacturing

# Map a single file (useful for testing)
f3next map \
  --file ./bom_recipes.csv \
  --doctype BOM \
  --project green-surface

# Query what the system knows about a doctype
f3next schema \
  --doctype "Sales Order" \
  --erp erpnext

# OS agent: natural language command
f3next command \
  --project green-surface \
  --cmd "Create a purchase order for 50kg epoxy from RM-EPOX-LIQ supplier"
```

### F3Next as MCP Server
Expose every major capability as an MCP tool so Claude, Cursor, and other MCP-compatible agents can call F3Next directly:

```
MCP tools exposed:
  f3next_implement(project_id, file_paths, erp_type, industry)
  f3next_map_file(file_content, doctype_hint, project_id)
  f3next_command(natural_language_command, project_id)
  f3next_query_erp(doctype, filters, project_id)
  f3next_get_schema(doctype, erp_type)
```

This turns F3Next from a standalone product into an **ERP operations platform that other agents can orchestrate** — a significant market opportunity.

---

## What Goes Away in V2

| V1 Component | V2 Replacement | Reason |
|---|---|---|
| `field_mappings.json` (schema facts) | Live REST API → Redis cache | Always accurate, version-matched, captures custom fields |
| `field_mappings.json` (synonyms) | LLM reasoning with live schema context | LLM generalizes; synonyms are brittle and incomplete |
| `field_mappings.json` (classifier hints) | Semantic search (pgvector) + LLM reasoning | Semantic search handles any language, any terminology |
| `erpnext_doctype_graph.json` | `erp_setup_graph` DB table | Queryable, updatable, multi-ERP, no code deploy needed |
| `erpnext_deafaults_baseline.json` | `erp_safe_defaults` DB table | Same data, now queryable and industry-contextual |
| `fold_child_tables()` heuristics | LLM mapping with full child table schema | LLM sees the actual child table structure and maps correctly |
| `apply_defaults_and_normalize()` hardcoding | LLM + `erp_safe_defaults` table | Defaults are looked up, not hardcoded |
| `_score_by_columns()` synonym matching | LLM classification with live schema | Replaced entirely by reasoning |
| `_keyword_hints_score()` | Semantic search | Replaced entirely by vector similarity |

---

## What Stays in V2

| V1 Component | Reason to Keep |
|---|---|
| Temporal workflow orchestration | Best-in-class durable execution. V2 nodes are still Temporal activities. |
| Human-in-the-loop signal gates | The product's UX differentiation. Stays. |
| CVS (Context Versioning Service) | Already agent-like. Feeds live company context to OS agent. |
| pgvector + RAG infrastructure | Expands in V2 — becomes the primary intelligence layer |
| ERP adapter interface | Already ERP-agnostic. V2 extends, doesn't replace. |
| Cloudflare R2 for file storage | Good infrastructure choice. Stays. |
| FastAPI + Next.js frontend | Stays. CLI/MCP are additions, not replacements. |
| F3iche playbook concept | Core intellectual asset. Moves from JSON files to pgvector. |

---

## Migration Path: V1 → V2

V2 is a separate branch. V1 stays in production. Migration is gradual:

```
Phase 1 (Branch): Implement feeding layers
  → erp_setup_graph and erp_safe_defaults tables
  → Schema caching service (Redis layer over adapter.get_doctype_schema)
  → Seed all V1 JSON file data into DB tables and pgvector

Phase 2 (Branch): Replace MAP node
  → Implement agentic LLM mapper with tool calling
  → Run in parallel with V1 mapper and compare outputs
  → Only switch when V2 output quality >= V1 on test suite

Phase 3 (Branch): Replace CLASSIFY and PLAN nodes
  → Remove deterministic scoring functions
  → Full agentic pipeline

Phase 4 (Branch): CLI + MCP layer
  → F3Next CLI
  → MCP server
  → Agent-to-agent integration testing

Phase 5 (Main): Cutover
  → V2 becomes main
  → V1 archived
```

---

## Summary: The Three Questions Every V2 Component Must Answer

Before any V2 component is built, it must answer:

1. **"Is this ERP-agnostic?"** — Does it reference `erpnext` anywhere in core logic? If yes, it's wrong.
2. **"Is this industry-agnostic?"** — Does it hardcode manufacturing/trading/construction assumptions? If yes, it's wrong.
3. **"Does this scale by data, not code?"** — Would adding a new ERP, industry, or doctype require a code change? If yes, it's wrong.

If the answer to all three is "no" — the component is V2-ready.

---

*For V1 architecture details, see [`ARCH_IMPLEMENTATION.md`](./ARCH_IMPLEMENTATION.md)*  
*For ERP adapter interface, see [`shared/erp_adapters/base.py`](../shared/erp_adapters/base.py)*  
*CLI and MCP layer detailed planning: TBD in `ARCH_V2_CLI.md`*
