# pgvector KB — Seeding & Chunk Design Plan

> **Context:** F3Next retrieves semantic context from `kb_embeddings` using `WHERE kb_source LIKE :prefix ORDER BY embedding <=> query LIMIT top_k`. If fewer rows exist than `top_k`, the fallback at line 150–161 of `loader.py` **silently drops the prefix filter and returns anything from the whole table** — cross-contamination. This plan fixes that and defines the full KB content strategy.

---

## Collection 1 — `f3iche_<id>` (per-niche)

### What we're embedding today (current seeder)
The `seed_f3iches.py` currently extracts these sections:
- `business_reality` → 1 chunk
- `critical_checks[]` → 1 chunk per item
- `known_workflows[]` / `workflows[]` → 1 chunk per item
- `regulatory_context` → 1 chunk

**Problem:** `manufacturing_project_chemical.json` (31 KB) likely produces only **4–7 chunks**. You ask for `top_k=5` → you barely get enough, and the fallback bug kicks in if any are missing.

### Target: minimum 12 chunks per f3iche

| Section | Chunk Strategy | Expected Count |
|---------|---------------|----------------|
| Business reality (overview) | 1 chunk, full text | 1 |
| Each workflow step | 1 chunk per step (split on workflow name) | 3–6 |
| Critical checks | 1 chunk per check item | 3–5 |
| Regulatory / compliance | 1 chunk | 0–1 |
| Key doctypes narrative | 1 chunk per major doctype group | 3–5 |
| Common pitfalls | 1 chunk | 1 |
| Naming / defaults conventions | 1 chunk | 1 |
| **Total** | | **12–20** |

### What to actually embed

**Do NOT embed the raw JSON as-is.** The JSON structure (`required_modules: [...]`) is terrible for semantic search because embeddings of `["Manufacturing", "Stock", "BOM"]` don't carry meaning.

**Convert JSON → narrative prose per section.** Example:

```
[F3iche] manufacturing_project_chemical
Section: work_order_workflow

In a chemical project manufacturing business, production begins with a Work Order
raised against a Bill of Materials (BOM). The Work Order specifies the target item,
required quantity, WIP warehouse, and FG warehouse. Raw materials are issued via
Stock Entry (Material Issue). On completion, a Stock Entry (Manufacture) transfers
finished goods. Batch tracking is mandatory — every output lot receives a Batch record
with expiry. Quality Inspection is triggered before goods are transferred to the
selling warehouse.
```

This is semantically rich and retrieval-meaningful. Raw JSON arrays are not.

### New sections to ADD to f3iche JSONs (expand the schema)

```json
{
  "pitfalls": ["pitfall 1 description", "pitfall 2 description"],
  "naming_conventions": "Series and naming expectations for this niche...",
  "doctype_narratives": {
    "Work Order": "How Work Orders work in this niche specifically...",
    "Batch": "Why Batch matters here — expiry, regulatory traceability...",
    "Quality Inspection": "..."
  }
}
```

---

## Collection 2 — `erpnext_module_docs` (replacing scraped `erpnext_docs`)

### Current state
`seed_erpnext_docs.py` scrapes `docs.frappe.io` → uncontrolled noise, generic, stale, no doctype metadata in chunks.

### Target: curated chunks from `module_docs.json`

**Strategy:** 1 chunk per doctype per module. Format:

```
[ERPNext Docs] Manufacturing Module
Doctype: Work Order
Purpose: Tracks production runs against a BOM.
Key fields: production_item, bom_no, qty, wip_warehouse, fg_warehouse, status
Workflow: Draft → Submitted → In Process → Completed
Business use: Raise Work Orders after customer order confirmation. Each Work Order
consumes raw materials from WIP warehouse and produces finished goods. System
validates BOM availability before submission.
```

**Why this format:** The doctype name + field names + workflow state + business use sentence together create a high-signal embedding that matches well against queries like "what does Work Order need for BOM setup" or "which fields are required for production tracking."

### Chunk count estimate

| Module | Doctypes | Chunks |
|--------|----------|--------|
| Manufacturing | ~8 key doctypes | 8 |
| Sales | ~6 | 6 |
| Purchase | ~5 | 5 |
| Stock | ~8 | 8 |
| Accounts | ~8 | 8 |
| HR | ~5 | 5 |
| Projects | ~4 | 4 |
| **Total** | | **~44–60 chunks** |

**This is plenty.** `top_k=5` against 44+ rows in `erpnext_module_docs` will always return 5 meaningful, doctype-specific chunks.

### `top_k` to use for this collection: `5`

---

## Collection 3 — `apqc_pcf`

### Current state
APQC Excel seeded → process categories → text chunks. Likely hundreds of rows but spread across all industries (healthcare, education, retail, etc.).

### Problem
When a chemical manufacturing company queries `apqc_pcf`, top hits might include retail PCF categories if the embedding space isn't well-separated. We need **industry-filtered retrieval**.

### Recommended fix: add `industry` tag to chunk header

```
[APQC PCF] Industry: Manufacturing
Category: 4.0 Produce Product
Subcategory: 4.1.2 Manage Production Schedule
Process: Sequence production runs to match customer delivery requirements, considering
machine availability, raw material stock, and batch constraints. Key KPIs: OEE,
schedule adherence rate.
```

This lets semantic search naturally rank manufacturing chunks higher for manufacturing queries.

### `top_k` to use for this collection: `5`

Typically 200–500 rows seeded; 5 is fine. No contamination risk — all APQC.

---

## Collection 4 — `company_<project_id>` (per-project, event-driven)

### What goes here

This collection is project-scoped and grows through the pipeline as more is known about the company. Two sources feed it:

1. **`note.txt`** — a free-text file optionally uploaded by the user alongside their data files. This is the highest-priority business context in the entire system.
2. **Company profile JSON** — the versioned `company_context_v{N}.json` in R2, built and enriched by the profile agent nodes.

**`kb_source`:** `company_<project_id>` (same prefix for both sources — queried together)

---

### Chunks to embed

| # | Source | Content | When created |
|---|--------|---------|-------------|
| 1 | `note.txt` | Raw verbatim note from user | Step 2 (file parse) or Step 7 (profile build) |
| 2 | Company profile summary | Prose: company name, industry, f3iche, size, business reality, context flags | Step 7 (after build_company_profile) — re-embedded on every version |
| 3 | Operational context | Prose: required modules, required doctypes, key workflows, naming hints | Step 7b (after enrich_company_profile) — re-embedded on every version |

**Total: 2–3 chunks per project.** `top_k=3` is the correct ask — never request more than guaranteed rows.

---

### Chunk format

**Chunk 1 — raw note:**
```
[Company Context] project_id: b6ff0b7f
Source: user_note  version: raw

<verbatim content of note.txt>
```

**Chunk 2 — profile summary:**
```
[Company Context] project_id: b6ff0b7f
Source: company_profile  version: 2  profile_version: 2

Company: GreenSurface Pvt Ltd. Industry: Chemical Manufacturing.
Business type (f3iche): manufacturing_project_chemical. Size: SME.
Business reality: GreenSurface produces specialty surface coatings in batch
production. Key ERP concern is batch traceability, expiry management, and
project-linked production runs. Regulatory: ISO 9001, GST-registered India.
Context flags: negative qty values in stock file, customer column has mixed names.
```

**Chunk 3 — operational context:**
```
[Company Context] project_id: b6ff0b7f
Source: operational_context  version: 2

Required ERPNext modules: Manufacturing, Stock, Selling, Buying, Accounts.
Required doctypes: Work Order, BOM, Batch, Item, Customer, Sales Order,
Purchase Order, Stock Entry, Quality Inspection.
Naming patterns: SO-, PO-, WO- series expected. WIP warehouse: WIP - GS.
FG warehouse: Finished Goods - GS. Batch mandatory on all stock entries.
```

---

### Versioning strategy — DELETE + INSERT (idempotent)

The company profile is versioned (`v1`, `v2`, `v3`...) — a new version is written at:
- Step 7 (`build_company_profile`) — v1 created
- Step 7b (`enrich_company_profile`) — v1 enriched in-place
- Step 11a (`merge_company_profile`) — vN+1 created from user edits

**Rule: every time a new profile version is committed, re-embed the company collection.**

Strategy: `DELETE WHERE kb_source = 'company_<project_id>'` then re-INSERT all chunks. This is safe because:
- There are only 2–3 chunks — deletion is instant
- The latest version is always what nodes should query — stale v1 chunks should not coexist with v2
- `note.txt` chunk is stable (never changes) — re-inserting it is harmless

```python
# Idempotent embed — always replaces previous version
async def seed_company_context(project_id, profile_dict, note_text=None):
    kb_source = f"company_{project_id}"
    # 1. Wipe all previous chunks for this project
    await session.execute(
        text("DELETE FROM kb_embeddings WHERE kb_source = :src"),
        {"src": kb_source}
    )
    chunks = []
    # 2. note.txt chunk (if provided)
    if note_text:
        chunks.append(build_note_chunk(project_id, note_text))
    # 3. Profile summary chunk
    chunks.append(build_profile_summary_chunk(project_id, profile_dict))
    # 4. Operational context chunk
    chunks.append(build_operational_chunk(project_id, profile_dict))
    # 5. Embed and insert
    for chunk in chunks:
        vec = await generate_embedding(chunk)
        await session.execute(INSERT_STMT, {"source": kb_source, "content": chunk, "vector": vec})
    await session.commit()
```

---

### Trigger points in the IS pipeline

```
Step 2  — fetch_clean_files
  If a file named note.txt / company_note.txt / about.txt is detected:
  → Flag it as company_note in manifest metadata
  → Do NOT embed yet (no project context available for good chunk header)

Step 7  — build_company_profile (after profile is written to DB + R2)
  → Call seed_company_context(project_id, profile_v1, note_text)
  → Embeds: note chunk (if present) + profile summary chunk
  → Deletes any previous company_<project_id> rows first

Step 7b — enrich_company_profile (after enrichment written)
  → Call seed_company_context(project_id, enriched_profile_v1, note_text)
  → Re-embeds all 3 chunks with enriched business_reality + data_quality_score

Step 11a — merge_company_profile (after user-edited vN+1 written)
  → Call seed_company_context(project_id, profile_vN+1, note_text)
  → Re-embeds with user corrections applied
```

> **Why re-embed at every trigger instead of only on version change?**
> Because the profile summary chunk content changes between Step 7 and Step 7b (data_quality_score, context_flags, recommended_customizations are added). The version number alone doesn't tell you if the semantic content changed — easiest to always replace.

---

### Where `note_text` comes from at embed time

At Steps 7, 7b, and 11a, the `r2_manifest_url` is available. The activity can re-read the manifest and extract `note.txt` content:

```python
file_contents = _load_file_contents_from_r2(r2_manifest_url)  # already exists
note_text = next(
    (v for k, v in file_contents.items()
     if k.lower() in {"note.txt", "company_note.txt", "about.txt"}),
    None
)
```

No new infrastructure needed — the manifest already holds all file contents.

---

### What nodes query this collection

Currently NO node queries `company_<project_id>`. That is a **planned addition** — once the collection is seeded, every node from Step 7 onwards should include it:

```python
# Add to build_company_profile, retrieve_industry_knowledge, build_target_structure
company_chunks = await rag_retrieve(
    query_text,
    f"company_{project_id}",
    top_k=3,   # exactly as many chunks as we embed
)
```

Company context chunks must be injected **first** in every LLM prompt — highest priority over all other KB sources.

### `top_k` to use: `3`

---

## Collection 5 — `industry_reality` (NEW — the missing layer)

### What this is
Industry-specific operational knowledge that isn't in APQC (too theoretical) and isn't in ERPNext docs (too system-specific). This is the "ground truth of how these businesses actually operate."

### Content sources

| Source | Content Type | Examples |
|--------|-------------|---------|
| Domain expert narratives | Written by us or consultants | "In chemical batch manufacturing, expiry date tracking is non-negotiable — here's why and how..." |
| Regulatory summaries | Summarized from official sources | "ISO 9001 requirements for batch record traceability in process manufacturing" |
| Industry reports (summarized) | Key takeaways embedded as prose | "Common ERP failure points in job-shop fabrication: BOM version control, routing complexity" |
| Real implementation case studies | Anonymized | "How a 50-person garment manufacturer structured their variant matrix in ERPNext" |

### Chunking strategy
- 1 chunk per topic per industry vertical
- 300–500 words per chunk (longer than other collections — these are narratives)
- Header: `[Industry Reality] industry: <name> topic: <topic>`

### `top_k` to use: `3–4`

This is supplementary color — not authoritative. A few strong chunks are better than many mediocre ones.

### How to build this initially
Write 5–10 narrative chunks per f3iche manually. This is not automated — it requires domain expertise. Start with `manufacturing_project_chemical` since that's the live test case.

---

## Seeding Pipeline (Revised)

```
seed_f3iches.py          → f3iche_<id>           (12–20 chunks/niche, prose sections)
seed_module_docs.py      → erpnext_module_docs    (1 chunk/doctype, replaces scraped)
seed_apqc.py             → apqc_pcf               (exists, add industry tag)
seed_industry_reality.py → industry_reality_<id>  (NEW, manual content, 5–10 chunks)
seed_company_context.py  → company_<project_id>   (NEW, per-project, 3 chunks)
```

---

## `top_k` Decision Table (per node, per collection)

| Node | Collection | top_k | Guaranteed rows | Safe? |
|------|------------|-------|-----------------|-------|
| infer_f3iche | `f3iche_*` | 3 | 12+ per niche | ✅ |
| build_company_profile | `apqc_pcf` | 5 | 200+ | ✅ |
| build_company_profile | `erpnext_module_docs` | 5 | 44+ | ✅ |
| build_company_profile | `f3iche_<id>` | 5 | 12+ | ✅ |
| retrieve_industry_knowledge | `apqc_pcf` | 5 | 200+ | ✅ |
| retrieve_industry_knowledge | `erpnext_module_docs` | 5 | 44+ | ✅ |
| retrieve_industry_knowledge | `f3iche_<id>` | 6 | 12+ | ✅ |
| retrieve_industry_knowledge | `industry_reality_*` | 4 | 5+ | ✅ |
| enrich_company_profile | `erpnext_module_docs` | 5 | 44+ | ✅ |
| enrich_company_profile | `f3iche_<id>` | 5 | 12+ | ✅ |
| build_target_structure | `erpnext_module_docs` | 4 | 44+ | ✅ |
| build_target_structure | `apqc_pcf` | 3 | 200+ | ✅ |

---

## Implementation Order

### Phase 0 — Bugs & Fixes (done)
- [x] **Fix contamination bug** in `loader.py` — remove silent full-table fallback (✅ done)

### Phase 1 — Company Context (highest value, enables per-project personalization)
1. Add `seed_company_context()` as a **shared utility** in `shared/kb_utils.py` (not a standalone script — called from pipeline activities)
2. Detect `note.txt` in file manifest inside `build_company_profile` and extract `note_text`
3. Call `seed_company_context()` at end of `build_company_profile`, `enrich_company_profile`, `merge_company_profile`
4. Add `company_<project_id>` RAG call (top_k=3) to `build_company_profile`, `retrieve_industry_knowledge`, `build_target_structure` — inject chunks first in LLM prompts

### Phase 2 — f3iche Chunks (fixes sparse collection problem)
5. Expand f3iche JSON schema: add `pitfalls[]`, `naming_conventions`, `doctype_narratives{}`
6. Rewrite `seed_f3iches.py` to produce prose chunks from expanded schema (target: 12–20/niche)
7. Re-seed all 4 existing f3iches

### Phase 3 — ERPNext Module Docs (replace noisy scraped content)
8. Regenerate `module_docs.json` content with full per-doctype depth (AI-assisted)
9. Write `seed_module_docs.py` (1 chunk/doctype, `kb_source = erpnext_module_docs`)
10. Update nodes to query `erpnext_module_docs` instead of `erpnext_docs`

### Phase 4 — APQC & Industry Reality
11. Re-seed `apqc_pcf` with industry tag in chunk headers
12. Author 5–10 `industry_reality` chunks per active f3iche
13. Write `seed_industry_reality.py`
14. Add `industry_reality_*` to `retrieve_industry_knowledge` RAG calls

### Phase 5 — top_k cleanup
15. Update all `rag_retrieve()` calls across IS activities to match the top_k decision table above
