# Core KB Philosophy & Stepwise Migration Guide

> **Created**: 2026-07-05  
> **Status**: Active execution doctrine  
> **Audience**: Coding agents, tech team, research team  
> **Read when**: Before any KB refactor, prompt migration, or “delete patch file” work

---

## Purpose of This Document

This doc captures **what we decided**, **why**, and **how to execute step-by-step** — without deleting legacy KB files until each step is proven **10/10** on core-only architecture.

Older reform docs (`02_PROPOSED_ARCHITECTURE.md`, `03_KB_STRUCTURE.md`, `04_IMPLEMENTATION_PLAN.md`) describe the target end state. **This doc is the operating manual for getting there safely.**

---

## North Star

**F3Next should work for any company, any terminology, with changes only when:**

1. A **new F3iche** (business model) is onboarded, or  
2. A **new ERP** (e.g. Odoo) is supported, or  
3. **Quarterly enrichment** of universal concept docs (optional)

**Never** when a new customer uploads different column names or filenames.

---

## Core Philosophy

### 1. JSON patch files are frozen prompts, not domain truth

Most KB JSON under `containers/knowledge_base/` was created because:

```
LLM alone was ambiguous on a real customer file
  → engineer added deterministic rules (cheap, fast)
  → next customer broke a different edge case
  → more rules
  → 150+ JSON files
```

Each patch file solved a **specific reliability gap**. Removing it without encoding that gap in a **structured prompt + output schema + guardrail code** will break production.

**Therefore:** We do not “delete and hope.” We **eliminate the need** for each patch, validate, then deprecate.

### 2. Let the LLM think; give it the right context

The scalable replacement for synonym lists, filename priors, and intent encyclopedias is:

| Layer | Role |
|-------|------|
| **Structured system prompt** | Job description, reasoning rules, failure modes each patch fixed |
| **Frappe live API** | Authoritative doctype fields, types, mandatory flags, labels |
| **F3iche JSON** | Industry workflow, terminology patterns, bottlenecks |
| **Doctype graph** | Setup order, dependencies, MVP relevance |
| **Company learning** | Per-project observed columns/filenames (DB + embeddings) |
| **Pydantic / JSON output schemas** | Stable enums downstream agents depend on |
| **Python guardrails** | Merge policy, link resolution, risk gates — not JSON |

### 3. Frappe live call is primary for ERP schema

For doctype structure and field metadata:

- **Primary:** `fetch_live_doctype_schema()` / ERP adapter `get_doctype_schema()`
- **Not primary:** `erpnext/schema/mapping/*.json` (148 files, ~90% duplicate of Frappe)

Fuzzy prose about fields (“this column usually means X in garment context”) can be **LLM-generated at runtime** from Frappe data + F3iche context — no hand-written JSON per doctype.

### 4. No direct deletion until step passes 10/10

**Hard rule for all coding agents:**

1. **Add** the new path (prompt module, live-schema-first code, feature flag).
2. **Run** golden matrix / harness for that step.
3. **Pass 10/10** (or agreed threshold) using **core KB only** for that layer.
4. **Only then** mark legacy file as deprecated (comments, docs) — physical deletion is a later cleanup phase.

Legacy files stay on disk until nothing imports them and tests prove parity.

---

## What Is Core KB (Allowlist)

These are the **only repo artifacts** the platform should depend on long-term.

### Tier 1 — Deterministic files (Research / ERP-owned)

| Path | Owner | Changes when |
|------|-------|--------------|
| `common/f3iches/*.json` | Research | New business model onboarded |
| `erpnext/erpnext_doctype_graph.json` | Research | New doctype in scope / new dependency |
| `erpnext/erpnext_deafaults_baseline.json` | Research | New ERP or regional defaults |
| `common/concepts/universal/*.md` *(planned)* | Research | Quarterly enrichment |
| `common/concepts/f3iche_specific/*.md` *(planned)* | Research | New F3iche or quarterly enrichment |
| Per-ERP mirror (`odoo/…`) | Research | New ERP supported |

### Tier 2 — Embeddings (pgvector, not repo JSON)

| `kb_source` / namespace | Seeded from | Changes when |
|-------------------------|-------------|--------------|
| `f3iche_<id>` | F3iche JSON + optional prose | New F3iche |
| `universal_concepts` | Concept docs | Quarterly |
| `f3iche_*` (industry) | F3iche-specific concept docs | New F3iche |
| `company_<project_id>` | Upload learning | Automatic per project |
| `apqc_pfc` | APQC seed script | Rare |

**Embedding rule:** Embed **business concepts and F3iche knowledge**. Do **not** embed doctype field lists that Frappe already provides.

### Tier 3 — Runtime knowledge (no repo files)

| Source | Purpose |
|--------|---------|
| Frappe live schema | Field truth for customer’s ERP |
| Company knowledge DB | Learned column → field mappings |
| CVS / discovery artifacts | Project-specific target structure |
| `node_bank` table | Structured implementation Q&A nodes |

### Tier 4 — Prompt modules in code (replaces patch JSON over time)

Not “KB files” — versioned Python/Markdown under agent packages:

- `containers/discovery/prompts.py` (+ future scoper prompts)
- `containers/os/clarity_agent/prompts.py`
- `containers/os/command_planner/` workflow templates or planner prompts
- `containers/implementation/mapping_agent/` classifier + mapper prompts

Stable **enums** (intent IDs, workflow template IDs) live in **code or Pydantic schemas**, not 800-line JSON synonym lists.

---

## What Is NOT Core (Deprecate over steps — do not delete first)

### IS mapping sprawl (~160 files)

| Path | Patch problem it solved | Replacement |
|------|---------------------------|-------------|
| `erpnext/schema/mapping/*.json` (148) | Column synonyms + field metadata | Frappe live + LLM mapper prompt + company learning |
| `classification/filename_priors.json` | Doctype from filename | LLM classifier + F3iche context |
| `classification/column_priors.json` | Doctype from columns | LLM classifier + F3iche context |
| `classification/global_hints.json` | Keyword → doctype hints | LLM + concept embeddings |
| `corpus/merge_policies.json` | Dedupe keys per doctype | Python in `corpus_merge.py` |
| `corpus/party_entity_rules.json` | Customer vs supplier split | Python in `party_rules.py` / entity resolver |
| `shared/*.json` | OS/IS policy | Python policy modules |
| `value_translation/*.json` | Legacy system (Tally) transforms | Python + LLM for edge cases |
| `validation_rules.json` (partial) | Pre-import validation | Live schema + code; keep only **regulatory** slices if needed |
| `erpnext/docs/module_docs.json` | ERP prose for RAG | Frappe data → LLM narrative |

### Discovery / OS patch JSON (5 files — demoted, not core)

These are **not** structural core. They are compressed prompts/guardrails. Eliminate **need** first, then deprecate.

| File | Original job | Why it doesn’t scale | Replacement |
|------|--------------|----------------------|-------------|
| `signals_registry.json` | Score F3iche from uploaded files before discovery chat | Discovery now runs first; registry causes false positives on generic ERP files | F3iche dir allowlist + LLM confirmation prompt with discovery transcript as **source of truth** |
| `mvp_bottleneck_map.json` | Pain → functional requirements (RAG fallback) | Too small, not F3iche-aware | F3iche bottleneck sections + `mvp_scoping.py` + structured LLM output |
| `discovery_taxonomy.py` | Closed tag vocabulary for discovery | Tags duplicated in prompts; import unused in activities | Structured JSON output (industry, model, scale, pain) — no `#Tag` enums |
| `intent_definitions.json` | Clarity intent taxonomy + synonyms | Already injected as prompt text; 886 lines of prompt library | Prompt module + intent enum in code + Frappe schema context |
| `command_patterns.json` | Multi-step ERP workflows (SO→DN→SI) | Workflow DAG not in Frappe API | Python workflow templates **or** LLM plan → validated `ExecutionPlan` |

---

## Patch → Prompt Translation (What Agents Must Preserve)

When replacing a JSON file, explicitly cover the **failure mode** it was added for.

### `signals_registry.json`

**Preserved in prompt/rules:**

- Discovery conversation overrides file-based inference when user stated industry/model.
- Generic files (PO, item list, customer master) must not override a specific F3iche (e.g. chemical vs garment).
- Valid F3iche IDs come from `common/f3iches/*.json`, not invented IDs.
- File/corpus evidence is **supporting**, not primary.

### `mvp_bottleneck_map.json`

**Status (2026-07-06):** Soft-deprecated. `DISCOVERY_USE_MVP_MAP_FALLBACK` defaults **false**.  
Canonical source: `containers/discovery/kb/archetype_catalog.json` + F3iche `bottlenecks[]` via `archetype_registry.py`.

**Preserved:**

- Output: `primary_bottleneck`, `functional_requirements[]`, `suggested_seed_doctypes[]`.
- Seed doctypes must respect F3iche `key_doctypes` and doctype graph **setup layers**.
- Day-1 MVP is a **subset**, not full F3iche mandatory list (see `mvp_scoping.py`).

### `discovery_taxonomy.py`

**Preserved:**

- Consultant behavior: one question at a time, no survey tone, suspicious scale combos flagged.
- Structured extraction fields: industry, strategy, scale, legacy system, pain.
- Broad F3iche: `trading | manufacturing | service` → narrow template via `niche_resolver.py`.

### `intent_definitions.json`

**Preserved in Clarity prompt:**

- Abbreviations: SO, PO, DN, SI, JE, PE, etc.
- Entity patterns: customer/supplier, items (qty/rate/uom), relative dates.
- Payment direction: receive vs pay inference.
- Stock entry type inference (transfer, manufacture, issue).
- Ambiguity: ask when required entities missing.
- Risk levels for submit/cancel/delete.
- **Stable `intent_id` enum** for Command Planner downstream.

### `command_patterns.json`

**Preserved in planner:**

- ERPNext lifecycle: draft → submit → linked docs via `create_from`.
- Step `depends_on` ordering.
- Submitted docs cannot be auto-deleted — rollback = cancel / inform user.
- Risk escalation and confirmation gates on submit/cancel/delete chains.

**Note:** Frappe replaces **field** knowledge, not **orchestration policy**. Planner needs templates or validated LLM-generated plans.

---

## Architecture Layers (Target Runtime)

```
Layer 0: Narrow F3iche registry (JSON files + embeddings)
         ↓
Layer 1: Company knowledge space (per project — automatic)
         ↓
Layer 2: Live ERP schema (Frappe API — PRIMARY)
         ↓
Layer 3: LLM inference (structured prompt + schema validation)
         ↓
Layer 4: Feedback / fine-tune (future, optional)
```

See `02_PROPOSED_ARCHITECTURE.md` for detail. This doc adds: **migrate one layer at a time with tests.**

---

## Stepwise Migration Plan (Reduced Steps)

Each step: **implement new path → test 10/10 → deprecate need for legacy → next step.**

Do **not** skip validation gates.

### Step 0 — Baseline & gates (before any refactor)

**Goal:** Know what “10/10” means.

**Actions:**

- Define golden matrix row(s): e.g. Green Surface 4th run, plus 2–3 terminology variations.
- Record current pass rate per agent (discovery, signals, mapping, clarity, import).
- Add feature flags env vars for “use legacy KB” vs “use new path” where needed.

**Pass gate:** Harness runs reproducibly; baseline documented in `docs/IS_V2_BACKLOG.md`.

---

### Step 1 — Lock core KB contract (documentation + loader boundaries)

**Goal:** Code knows what Tier-1 core is; stop new patch entries.

**Actions:**

- Treat allowlist in this doc as authoritative for new work.
- Context engine / agents: document which tiers they load (see `shared/context_engine/loader.py`).
- **Freeze:** no new files under `schema/mapping/`, no new signals in `signals_registry.json`.

**Pass gate:** Team agreement; no new patch PRs.

---

### Step 2 — Discovery: structured extraction without tag dependency

**Goal:** Discovery works with prompts + coverage JSON only; taxonomy file unused.

**Try:**

- Rely on `discovery/prompts.py` structured output (industry, strategy, scale, legacy, pain, f3iche_hint).
- Remove reliance on `#Ind_*` tags in recommendation (use coverage text + `mvp_focus`).
- Expand `mvp_scoping.py` for bottleneck → Day-1 seeds (target: replace `mvp_bottleneck_map.json` **need**).
- `build_target.py` already uses F3iche + doctype graph — validate end-to-end at discovery completion.

**Legacy still loaded:** `mvp_bottleneck_map.json` as RAG fallback until Step 2 passes.

**Pass gate:** 10/10 discovery → recommendation → target structure on golden discovery transcripts **without** reading `discovery_taxonomy.py` or `mvp_bottleneck_map.json`.

---

### Step 3 — F3iche resolution: discovery-first, retire registry scoring need

**Goal:** F3iche confirmation uses discovery + F3iche catalog; registry optional.

**Try:**

- Allowlist from `list_f3iche_template_ids()` / `common/f3iches/`.
- Prompt: discovery transcript = source of truth; corpus = supporting.
- `niche_resolver.py` for broad → narrow mapping.
- Feature flag: `F3ICHE_USE_REGISTRY_SCORING=false` skips `score_manifest()`.

**Legacy still loaded:** `signals_registry.json` when flag true.

**Pass gate:** 10/10 F3iche confirmation on golden projects with flag false.

---

### Step 4 — IS mapping: live schema primary for one doctype, then all

**Goal:** Eliminate need for `mapping/*.json` for covered doctypes.

**Try:**

- Flip order in mapping agent: Frappe first, KB mapping as fallback (then remove fallback per doctype after pass).
- LLM classifier prompt: filename + columns + sample + F3iche + doctype graph layer list.
- LLM mapper prompt: live schema fields + F3iche terminology + company learning.
- Migrate merge/party rules to Python only (already partially done).

**Pass gate:** 10/10 classify + map on golden files for MVP doctype set with **no** `mapping/{Doctype}.json` reads.

---

### Step 5 — OS Clarity: prompt module replaces intent JSON need

**Goal:** Clarity works with prompt module + Frappe context; intent JSON unused.

**Try:**

- Move `intent_summary_for_prompt()` content to `prompts.py` or `intent_catalog.py` (code).
- Keep Pydantic output schema with fixed `intent_id` enum.
- Optional: inject live doctype list from Frappe for customer site.

**Legacy still loaded:** `intent_definitions.json` when flag true.

**Pass gate:** 10/10 intent + entity extraction on OS command test set with flag false.

---

### Step 6 — OS Command Planner: templates or validated LLM plans

**Goal:** Multi-step workflows without `command_patterns.json`.

**Try (pick one, test both if time):**

- **Hybrid (recommended):** ~10 workflow templates in Python; LLM selects template ID.
- **Full LLM:** Generate `ExecutionPlan` JSON; validate against doctype graph + Frappe.

**Pass gate:** 10/10 multi-step plans (sales cycle, purchase cycle, manufacture) on test prompts.

---

### Step 7 — Embeddings: F3iche + concepts only

**Goal:** Vector store supports core KB; no dependency on industry chunk Python files for IS path.

**Try:**

- Seed `f3iche_*` from JSON + prose.
- Add `universal_concepts` when concept docs exist.
- Stop seeding redundant ERP field docs when live schema path is proven.

**Pass gate:** RAG retrieval improves or matches baseline on bottleneck/MVP questions.

---

### Step 8 — Deprecation cleanup (only after Steps 2–7 pass)

**Goal:** Remove dead imports and files.

**Actions:**

- Grep for zero imports per file.
- Delete in small PRs per category (mapping folder last).
- Update `ARCH_KNOWLEDGE_BASE.md` and backlog.

**Pass gate:** Full golden matrix 10/10 on CI with core KB only.

---

## Testing Doctrine (Every Step)

### What “10/10” means

For the step under test:

- All golden matrix cases for that **agent/layer** pass.
- No regression in downstream agents (discovery → target → signals → mapping → import).
- Terminology **variation** cases pass (different filenames/columns, same intent).
- Legacy path can remain in repo but must not be **required** for pass.

### What to run

- Project-specific golden data (e.g. `attachments/green-surface/...`).
- Unit tests for scorers, resolvers, plan builder.
- After L0 prompt changes: `python -m shared.smoke_llm` (per architecture rules).
- Update one line in `docs/IS_V2_BACKLOG.md` per completed step.

### Feature flags (recommended pattern)

```
F3ICHE_USE_REGISTRY_SCORING=true|false
MAPPING_LIVE_SCHEMA_PRIMARY=true|false
CLARITY_USE_INTENT_JSON=true|false
PLANNER_USE_COMMAND_PATTERNS_JSON=true|false
```

New path default **false** until 10/10; then flip default to **true**.

---

## What Coding Agents Should NOT Do

- ❌ Delete `schema/mapping/` or any patch JSON “because reform doc says so”
- ❌ Add new synonyms to mapping files or signals_registry
- ❌ Big-bang rewrite of all agents in one PR
- ❌ Mark UI complete when import returned `steps_failed > 0`
- ❌ Use filename-only priors without KB promotion path (architecture rule)
- ❌ Skip golden matrix because “LLM should work”

## What Coding Agents SHOULD Do

- ✅ Read this doc + `docs/FOUNDATIONS.md` before KB-related changes
- ✅ One step per PR where possible; feature flag for new path
- ✅ Document which patch failure mode the prompt covers (comment or step doc)
- ✅ Prefer live Frappe schema over static JSON for field metadata
- ✅ Keep F3iche JSON and doctype graph as single source of truth for business/ERP ordering
- ✅ Validate 10/10 before flipping flags or deprecating imports

---

## Success Metrics (Reform Complete)

| Metric | Target |
|--------|--------|
| New customer upload | 0 KB file changes |
| New F3iche | 1 JSON + 2–3 concept docs + re-embed |
| New ERPNext doctype in scope | 0 mapping files; optional graph entry |
| New ERP (Odoo) | 1 doctype graph + 1 defaults baseline |
| KB JSON count (repo) | Core only (~F3iches + graph + defaults + concepts) |
| Mapping accuracy | ≥90% first upload; ≥95% after company learning |

---

## Related Documents

| Doc | Use when |
|-----|----------|
| [00_OVERVIEW.md](00_OVERVIEW.md) | Executive context |
| [01_CURRENT_STATE_AUDIT.md](01_CURRENT_STATE_AUDIT.md) | Why patches exist |
| [02_PROPOSED_ARCHITECTURE.md](02_PROPOSED_ARCHITECTURE.md) | Layer model detail |
| [03_KB_STRUCTURE.md](03_KB_STRUCTURE.md) | File templates (F3iche, concepts) |
| [04_IMPLEMENTATION_PLAN.md](04_IMPLEMENTATION_PLAN.md) | Original week plan (superseded by steps above for KB work) |
| [docs/FOUNDATIONS.md](../FOUNDATIONS.md) | Layer/pillar triage on every issue |

---

## Summary for Agents (TL;DR)

1. **Core KB** = F3iche JSONs + doctype graph + defaults + concept embeddings + runtime (Frappe + company learning).
2. **Patch JSON** = frozen prompts; eliminate **need** via structured prompts + schemas + Python guardrails.
3. **Never delete first** — add new path, test 10/10, flip flag, then deprecate.
4. **Execute Steps 0→8** in order; each step has a pass gate.
5. **Frappe live schema is primary** for ERP fields; LLM fills terminology gaps using F3iche + company context.

When in doubt: ask *“Which foundation layer is broken?”* not *“Which JSON line is wrong?”*
