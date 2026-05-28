# ERP data integration architecture
_Exported on 5/24/2026 at 22:37:10 GMT+5:30 from Cursor (3.2.16)_

---

**User**

# <the problem i faced> - 
During Step 13: Transactional Data (Phase C), the system attempted to sync two Work Order documents into the ERPNext instance ([https://green-surface.f3next.in](https://green-surface.f3next.in)), but both failed:
Plaintext

INFO:httpx:HTTP Request: POST https://green-surface.f3next.in/api/resource/Work%20Order "HTTP/1.1 417 Expectation Failed"
ERROR:temporalio.activity: ❌ ERPNext API Error on Work Order row 0: ERPNext error 417: LinkValidationError: frappe.exceptions.LinkValidationError: Could not find Work-in-Progress Warehouse: WIP - Factory

    Why it happened: ERPNext threw a 417 Expectation Failed because the Work Order payload explicitly references a source warehouse called WIP - Factory, which does not exist in the live target site.

#<the idea/question i came up with >
why cant we ask for data present in erpnext db via api call instead of directly writing something we dont know about (btw does cvs keeps the erpnext data or not?) - like even if there is spelling mismatch or that required field isnt present LLM will do the job accordingly !
then i had a simple question that what exactly is needed here what are the possibilities and scenarios so that we can build an architecture on top of that - so i asked this to a context less Gemini LLM : and it gave me these answers 
i want you to go through the response of gemini - crosscheck it with our project/repo, take the basic idea and make it project-fit if it really is helpful - add some of your own points and review - and also tell how close is our system/project currently towards this plan !

#<gemini conversation>
me - cant we do like this - 
1. when we have the plan or required fields for any doctype we are going to create - then we will also get the data from the erpnext ? like if work order needs warehouse setup then we will get all the warehouses transactions from erpnext via api call and then LLM will decide which one to write - this will also work when spelling mistakes are there !
and this is how global product's systems work, these days, right ?


we need to create some architecture or some plan for such cases 
there are only these possibilities right ?:
1. the X doctype needs Y as required field - 
a. it is either present in the erpnext db as provided by the user data
b. it is either there but with some different spelling - LLM work needed to match it with that
c. or it is not present and we need to create it !

to do that we need to have these things -
1. how erpnext or any erp software works - how company onboards/new client gets implemented into it !
2. required fields and doctypes for any doctype/module/master
3. we also need to continuously know about the data in the erpnext to satisfy the first a,b,c points !




just write down all the possibilities or the basic if/else's for any ERP system - i have written a few - would those are the final complete everything we need to automate implementation for any erp software ???


gemini- Here is your reality check: your intuition is brilliant, but those three possibilities are only about 20% of the actual logic required to automate an ERP.

You have perfectly described a **1-to-1 foreign key resolution loop**. And yes, this "Read Live State -> Diff against Intent -> Fuzzy Match via LLM -> Execute" loop is exactly how modern, global AI products (like autonomous integration agents) work.

However, ERP systems are not flat databases. They are massive webs of hierarchical, conditional, and stateful logic. If you build your automation engine using only those three `if/else` branches, it will crash the moment it hits a real-world business constraint.

Here is the complete matrix of possibilities you must account for to build a truly autonomous ERP implementation system.

### The Complete ERP Data Resolution Matrix

When Doctype X (e.g., Work Order) requires Field Y (e.g., Warehouse), here are the actual possibilities your AI needs to handle:

| Scenario | Condition | System Action Required |
| --- | --- | --- |
| **1. Exact Match** | Y is in the ERP and spelled perfectly. | **Bind & Execute:** Map the ID and proceed. |
| **2. Fuzzy Match** | Y is spelled differently (e.g., "Whouse 1" vs "Warehouse 1"). | **LLM Resolution:** LLM calculates string distance/semantic similarity and maps to the correct ID. |
| **3. Duplicate Conflict** | Y matches *multiple* active records (e.g., "Tata" matches "Tata Motors" and "Tata Steel"). | **Clarification:** The AI must halt and ask the user (or check surrounding context) to break the tie. Do *not* let the LLM guess. |
| **4. State Violation** | Y exists perfectly, but its state is invalid (e.g., the Warehouse is disabled, or the Supplier is "On Hold"). | **State Override or Halt:** The AI must check if it has permission to reactivate the record, otherwise, flag an error to the user. |
| **5. Rule Violation** | Y exists, but breaks a business rule (e.g., User selects "Office Supplies" item, but that item isn't checked as "Is Manufacturing Item" for a BOM). | **Config Patch:** The AI must update the existing record (check the box) before it can use it in the parent transaction. |
| **6. Simple Missing** | Y is missing and has no dependencies. | **Auto-Create:** Create Y immediately. |
| **7. Cascading Missing (The Trap)** | Y is missing, but to create Y, you need Z (e.g., to create a missing Warehouse, you need to assign a Company and an Account). | **Recursive Creation:** The AI must recursively pause X, resolve Z, create Y, and then resume X. |

---

### The Architecture You Need to Build This

To satisfy your three prerequisites (knowing ERP logic, required fields, and live data), your system architecture needs three distinct components working together:

1. **The Schema Graph (Knowledge of required fields):** You need a static representation of the ERP's database structure. The system needs to know *before* it tries to do anything that "Work Order" depends on "Item" and "Warehouse".
2. **The Live Context Sync (Knowledge of live data):** You cannot query the ERP API for every single LLM decision; the latency will destroy your user experience. You need a background worker that listens to the ERP via webhooks and maintains a cached "snapshot" of all active Master Data (Items, Customers, Warehouses) in a fast layer like Redis.
3. **The LLM Router (The Decision Maker):** When a user command comes in, the LLM reads the user's messy text, looks at the fast Redis snapshot of existing records, runs the 7-step matrix above, and outputs a clean JSON payload.

You are on the exact right track for building an autonomous system. The jump from a basic script to an enterprise-grade AI agent is simply handling scenarios 3, 4, 5, and 7.

How do you want to handle Scenario 7 (Cascading Dependencies) in your pipeline—should the AI silently try to generate the missing parent data, or should it immediately ask the user for the missing context?


me- lets write it/ organize it/ architect it in a clean understandable way !

1. you talked about state - so we need to have the idea of state too while making the api call - i want to know more about the what are the things we have access to while calling the api - like what things are open - like what erpnext or any erp's api gives us permission to do ?

2. and then every erp data resolution matrix scenarios 

3. and at the example of it working in every situations - 
i would say we should have idea about every possible situation first to derive the matrix and architecture for it !


take your time and write the best architecture - we want logical and truthful for any erp agnostic (mention if things are no erp agnostic and specific for any erp differently) - we are writing the foundation of our system !


gemini- lets write it/ organize it/ architect it in a clean understandable way !

1. you talked about state - so we need to have the idea of state too while making the api call - i want to know more about the what are the things we have access to while calling the api - like what things are open - like what erpnext or any erp's api gives us permission to do ?

2. and then every erp data resolution matrix scenarios 

3. and at the example of it working in every situations - 
i would say we should have idea about every possible situation first to derive the matrix and architecture for it !


take your time and write the best architecture - we want logical and truthful for any erp agnostic (mention if things are no erp agnostic and specific for any erp differently) - we are writing the foundation of our system !

---

**Cursor**

Let me explore the codebase thoroughly before giving you a grounded answer.

Now let me look at the context engine and OS agent to understand the full picture.

Now I have a complete picture. Let me give you a thorough analysis.

---

## The Gemini Analysis: What's Right, What's Missing, and Where F3Next Actually Stands

### First, your direct question: Does CVS keep the ERPNext data?

**Yes, absolutely.** The CVS (`containers/context_versioning/`) is exactly the "Live Context Sync" component Gemini described. It:
- Fetches all warehouses, customers, suppliers, items, cost centers from your live ERPNext instance
- Stores them as a versioned JSONB snapshot in Supabase (`context_snapshots` table)
- Caches them in Redis for the OS agent
- Keeps them fresh via Frappe webhooks + a cron poller

The OS agent already does "Read Live State → Decide → Execute" for every natural language command. **The Implementation System (IS), however, does NOT yet fully do this during Phase C imports.** That's the gap the WIP Warehouse error exposed.

---

### The Gemini 7-Scenario Matrix — Mapped to F3Next Reality

| # | Scenario | What Should Happen | F3Next Status |
|---|---|---|---|
| 1 | **Exact Match** | Bind & Execute | ✅ Done everywhere |
| 2 | **Fuzzy Match** (spelling mismatch) | LLM or semantic similarity resolve | ⚠️ Partial — `_resolve_link_references` does deterministic string pattern matching only (`WIP - Factory` → tries `WIP - %`) |
| 3 | **Duplicate Conflict** (matches >1 record) | Halt, ask user | ❌ Missing — `list_records(..., limit=1)` silently takes the first match |
| 4 | **State Violation** (record disabled / on hold) | Check state, override or halt | ⚠️ Partial — CVS filters `disabled=0` for OS context, but IS pipeline doesn't check this before creating link references |
| 5 | **Rule Violation** (record exists but needs a config flag set) | Patch existing record first | ❌ Not implemented |
| 6 | **Simple Missing** (no dependencies) | Auto-create | ✅ Done — `_dynamic_seed_doctype()` in Pass 2 of `execute_import_phase` |
| 7 | **Cascading Missing** (needs Z to create Y to satisfy X) | Recursive resolution | ⚠️ Partial — `_DYNAMIC_SEED_BLACKLIST` prevents attempts on complex types (Warehouse, Account), but doesn't recursively resolve them |

**Your specific WIP bug was Scenario 2.** `WIP - Factory` ≠ `WIP - GS`. The `_resolve_link_references` method does try to match this — it tries:
1. Exact: `WIP - Factory` → No
2. Suffix: `WIP - Factory - %` → No
3. Base split: `WIP - %` → Should find `WIP - GS` → ✅

The reason it still failed is likely one of these:
- The `_resolve_link_references` call wraps everything in a broad `except Exception → pass` which silently swallows resolution failures and returns the original unchanged data
- Child table fields (nested rows inside a Work Order) are **not** recursively resolved — only top-level fields on the parent doctype are processed

---

### The Gemini 3-Component Architecture — Where F3Next Already Has Each One

Gemini described three required components. Here's the honest mapping:

**Component 1: Schema Graph (static knowledge of required fields)**

F3Next has this as `erpnext_doctype_graph.json` + `field_mappings.json` in `containers/knowledge_base/erpnext/`. These define every doctype's phase, dependencies, seeding complexity, and link fields. The `_build_link_field_index()` in `import_agent/activities.py` loads this at startup. **This is fully built.**

**Component 2: Live Context Sync (cached snapshot of live data)**

F3Next has this as the entire CVS subsystem — Supabase snapshots, Redis caching, webhook triggers, cron polling. The `fetch_master_data()` in `shared/erp_adapters/erpnext.py` is the exact "background worker" Gemini described. **This is fully built for the OS agent.** The IS pipeline does live queries per-row via `_resolve_link_references`, but doesn't use the CVS snapshot.

**Component 3: LLM Router (decision maker)**

F3Next has `llm_router.py` + the entire OS 9-step pipeline. The OS agent consults the CVS snapshot before generating any payload. **Fully built for OS.** The IS pipeline does NOT use the LLM for link resolution — it uses deterministic string matching only.

---

### The Actual Architectural Gap Gemini's Idea Reveals

Gemini's core insight — "query live ERPNext before writing so LLM can decide" — is already the OS agent's design. The IS pipeline (Phase C imports) was designed differently: it assumed the data coming from the user's files is already clean, and the pre-flight seeder (Pass 1 + Pass 2) would handle missing lookups before the main import loop.

What's missing is a **Pre-resolution step inside the IS import loop** that applies the same Read→Diff→Resolve logic the OS agent uses, but for batch import rows. Specifically:

For each row about to be imported:
1. Identify all Link fields in the payload (already done via `_KNOWN_LINK_FIELDS`)
2. For each Link field value, query ERPNext for the exact name → if found, proceed
3. If not found → query for fuzzy/partial matches → if one clear match, substitute
4. If multiple matches → log a warning and skip the row, or use the closest
5. If none at all → check if it's in `_DYNAMIC_SEED_BLACKLIST` → if not, auto-create it
6. If it's blacklisted (complex type like Warehouse, Account) → flag as a data gap requiring manual review

This loop is what `_resolve_link_references` is trying to do, but it runs inside `create_record` (too late, after the payload is assembled), wraps errors silently, and doesn't handle child tables.

---

### Points Gemini Missed That Are Worth Adding

**1. ERPNext's API surface is broader than CRUD.** Beyond `/api/resource/`, ERPNext exposes:
- `/api/method/` — custom server-side methods (e.g., `frappe.client.get_value`, `frappe.desk.form.load.getdoc`)
- Doctype-level validators that run server-side before saving — your 417 is this; it's not a client error, it's Frappe's pre-save validation firing
- Submit/Cancel docstatus transitions (docstatus 0→1→2) — which the adapter already handles via `submit_document`/`cancel_document`

**2. Company abbreviation is ERPNext-specific, not ERP-agnostic.** The `WIP - GS` pattern is Frappe's naming convention where every warehouse, cost center, and account automatically gets appended with the company abbreviation. This is unique to Frappe/ERPNext. For SAP it would be different; for Odoo, different again. Your `_resolve_link_references` already accounts for this with the `- %` suffix pattern — but it's not documented as an ERPNext-specific rule.

**3. Gemini's "Redis snapshot" advice applies already in OS, but IS needs a read-before-write step.** During IS Phase C execution, instead of querying ERPNext per-row inside `create_record`, a better approach would be to do one bulk pre-resolution pass: fetch all warehouses, all items, all customers from ERPNext once before the loop, build an in-memory lookup dict, then resolve all rows against that dict before the import loop starts. This avoids N+1 API calls and is faster.

**4. Cascading dependency (Scenario 7) is the hardest and Gemini undersells it.** In ERPNext, creating a Warehouse requires: Company (must exist), Parent Warehouse (must exist and `is_group=1`), Warehouse Type (optional but linked). Your `seed_from_config` in `ERPNextAdapter` already handles the Warehouse case specifically — it queries existing warehouses, extracts the company abbreviation, then creates child warehouses under the correct parent. This is recursive creation done manually. The gap is that it's hardcoded for Warehouse only; a general-purpose recursive resolver would need to walk the doctype graph.

---

### Honest Assessment: How Close Is F3Next to the Full Plan?

| Gemini Component | F3Next Progress |
|---|---|
| Schema Graph | ~90% — graph + field_mappings exist, but child-table link fields aren't all indexed |
| Live Context Sync | ~95% for OS, ~40% for IS (IS does per-row live queries, not a pre-resolved snapshot) |
| LLM Router | ~90% — fully operational, but IS pipeline doesn't involve LLM in link resolution |
| Scenario 1 (Exact Match) | ~100% |
| Scenario 2 (Fuzzy Match) | ~50% — string pattern only, no LLM, no child-table coverage |
| Scenario 3 (Duplicate Conflict) | ~5% — silently picks first match |
| Scenario 4 (State Violation) | ~30% — CVS filters disabled, but IS doesn't check |
| Scenario 5 (Rule Violation) | ~0% |
| Scenario 6 (Simple Missing) | ~85% — `_dynamic_seed_doctype` works well |
| Scenario 7 (Cascading Missing) | ~40% — Warehouse+FiscalYear are hardcoded, general case not handled |

**Overall: F3Next is at roughly 65-70% of the full architecture Gemini described.** The OS agent is at ~90%. The IS pipeline is the weaker area, specifically for Phase C transactional data where link references to real warehouse/account names from the source company don't cleanly map to the target instance.

The most impactful next step to close the gap is a **bulk pre-resolution pass in `execute_import_phase`** — before the row-by-row import loop — that:
1. Fetches all known records for all linked doctypes referenced in the phase's rows (one query per doctype, not per row)
2. Builds an in-memory resolution map
3. Rewrites every row's link fields using that map with fuzzy/base-name matching
4. Flags unresolvable references as skipped rows with a reason, rather than letting ERPNext throw 417

This would solve the WIP Warehouse problem and every similar case in Phase C — and it fits cleanly into the existing Pass 1 / Pass 2 / main loop architecture that's already in `execute_import_phase`.

---

**User**

write a detailed implementation plan to work on this !
we will create a separate branch for this !
keeping the project/codebase's structure in mind ! and our goal too !

---

**Cursor**

Let me do a focused read of the key files before writing the plan.

Now I have everything I need. Let me create the plan.

---

**User**

Implement the plan as specified, it is attached for your reference. Do NOT edit the plan file itself.

To-do's from the plan have already been created. Do not create them again. Mark them as in_progress as you work, starting with the first one. Don't stop until you have completed all the to-dos.

---

**Cursor**

I'll start on the branch and work through the plan in order.


Creating the link resolver module and wiring it into the import pipeline.


Adding the bulk pre-resolve helper and wiring Pass 2.5 into the import activity.


Resolution logic verified. Marking todos complete and committing.


All todos are done on branch `feature/is-link-resolution-v2` (commit `af11915`). Summary:

## What was implemented

### 1. New: [`shared/erp_adapters/link_resolver.py`](shared/erp_adapters/link_resolver.py)
- `ResolutionMap` / `ResolutionResult` dataclasses
- `resolve_single()` — exact → suffix/base-name → normalized match
- `BulkLinkResolver.build_resolution_map()` — one `list_records` call per linked doctype
- `collect_link_targets_from_rows()` — scans top-level and nested child table rows
- `apply_resolution_map_to_rows()` — rewrites payloads before import

Verified: `resolve_single('WIP - Factory', ['WIP - GS', 'Stores - GS'])` → `'WIP - GS'`

### 2. Modified: [`containers/implementation/import_agent/activities.py`](containers/implementation/import_agent/activities.py)
- **`Pass 2.5`** runs after Pass 2, before the main import loop
- `_bulk_pre_resolve_phase_rows()` collects all link targets, builds one resolution map, rewrites rows into `_pre_resolved_cache`
- Main loop reads from cache when available
- Each step's `execution_logs` entry includes `resolution_summary` (corrections, unresolvable values, ambiguous picks)

### 3. Modified: [`shared/erp_adapters/erpnext.py`](shared/erp_adapters/erpnext.py)
- `_schema_cache` and `_link_names_cache` on the adapter instance
- `_resolve_link_references()` now:
  - Recurses into child table rows
  - Uses cached schemas and bulk-fetched link names
  - Uses shared `resolve_single()` logic
  - Logs **warnings** instead of silently swallowing failures

## New import flow

```
Pass 1 → Pass 1B → Pass 2 → Pass 2.5 (NEW) → Main Loop
                              ↓
                    bulk fetch + rewrite rows
                    (WIP - Factory → WIP - GS)
```

## How to test

Re-run Phase C on `green-surface.f3next.in`. Work Orders with `wip_warehouse: "WIP - Factory"` should resolve to `"WIP - GS"` before POST. Check Temporal logs for `Pass 2.5` lines and `resolution_summary` in execution logs.

---

**User**

now how am i supposed to check this ?
some data is already imported in erpnext - should i create another dummy data ?
and check with that ?
if yes then give me a prompt talking about the changes we just did so that the agent that created the earlier dummy data csv files would create more accordingly !

or propose your option if you have

---

**Cursor**

Checking how Phase C imports work and what test data already exists so I can recommend a practical verification approach.


You do **not** need a full new onboarding run. The fastest path is to **re-run Phase C on the existing Green Surface session** — the same mapped R2 payloads that failed should now pass through Pass 2.5.

## Recommended approach (fastest)

### Option A — Re-run Phase C on existing data (recommended)

Your original Work Order rows in R2 likely still have `wip_warehouse: "WIP - Factory"`. That is exactly what Pass 2.5 is built to fix. You do not need new CSVs unless you want a cleaner, isolated proof.

**Steps:**

1. **Make sure the new code is running**
   - If testing via **UI/Temporal**: rebuild and restart `implementation_worker`
   - If testing locally: use `is_harness` (runs repo code directly, no Docker worker needed)

2. **Re-run only Phase C** using the existing Green Surface fixture:

```bash
# From repo root — LIVE run against green-surface ERPNext
python -m containers.implementation.is_harness --step execute_import_phase --phase phase_c_transactional
```

Fixture already points at your project ([`containers/implementation/dev_fixtures/execute_import_phase.json`](containers/implementation/dev_fixtures/execute_import_phase.json)):
- `session_id`: `3145be35-2991-48dd-b43e-e59df9e86f5c`
- `project_id`: `b6ff0b7f-a616-4179-8f68-deda9b3578af`
- `company_slug`: `green-surface`

Set `"dry_run": false` in that fixture (or override via harness if supported). **Important:** `--dry-run` skips Pass 2.5 entirely — it only runs when `not dry_run and base_url`.

3. **Watch the logs for these lines:**

```
🔗  PASS 2.5 — Bulk link pre-resolution
Pass 2.5 — Bulk resolving N doctype(s): Warehouse, ...
BulkLinkResolver: Warehouse 'WIP - Factory' -> 'WIP - GS'
Pass 2.5: resolved Work Order.wip_warehouse 'WIP - Factory' -> 'WIP - GS'
```

4. **Check the result JSON** — each step's `execution_logs` should include:

```json
"resolution_summary": {
  "resolved_count": 2,
  "corrections": [
    {
      "field": "wip_warehouse",
      "target_doctype": "Warehouse",
      "original": "WIP - Factory",
      "corrected": "WIP - GS"
    }
  ],
  "unresolvable_values": []
}
```

5. **Verify in ERPNext** — open Work Orders on `green-surface.f3next.in` and confirm new ones were created (or existing ones counted as `already_exists`).

**About already-imported data:** Re-running Phase C will touch all transactional doctypes in that phase, not just Work Order. Rows that already exist are treated as success (`already_exists`). Rows that **failed before** (like your 2 Work Orders) are the ones that should now succeed.

---

### Option B — Add 2–3 new Work Order rows (cleaner proof)

Use this if you want unmistakable evidence without wading through duplicate noise from other doctypes.

You only need a **small supplemental CSV**, not a full dummy dataset. Upload it as an additional file or append rows to the existing Work Order mapping — the key is **new unique Work Order names** with **intentionally wrong warehouse suffixes**.

---

## Prompt for the agent that created your dummy CSVs

Copy-paste this:

---

**Context:** We added IS Link Resolution V2 (Pass 2.5) to the F3Next import pipeline. Before creating Work Orders in ERPNext, the system now bulk-fetches live Warehouse/Item/Customer names from the target site and auto-resolves mismatched link fields. Example: source CSV has `wip_warehouse = "WIP - Factory"` but the live ERPNext site has `"WIP - GS"` — the import should rewrite it automatically before POST.

**Task:** Create a **small supplemental test CSV** (2–3 rows only) for **Work Order** import on the existing **Green Surface / manufacturing** project. Do **not** recreate the full dummy dataset — only new rows to validate link resolution.

**Requirements:**

1. **New unique identifiers** — use Work Order names/IDs that do not exist in ERPNext yet, e.g. `WO-TEST-LINK-001`, `WO-TEST-LINK-002`.

2. **Intentionally mismatched warehouse names** (this is the test):
   - `wip_warehouse`: use `"WIP - Factory"` (wrong suffix — target site uses company abbr, e.g. `"WIP - GS"`)
   - `fg_warehouse`: use `"Finished Goods - Main Plant"` or `"Stores - Factory"` (also wrong suffix)
   - Do **not** use the correct live names — we want to prove auto-resolution

3. **Valid references that already exist on green-surface.f3next.in:**
   - `production_item` — use an Item code already imported in Phase B
   - `bom_no` — use a BOM already linked to that item
   - `company` — use the live company name on the site
   - `qty` — small number, e.g. 10 or 100

4. **Optional second scenario row:** one row with a **slightly misspelled** warehouse, e.g. `"WIP-Factory"` (no spaces) or `"wip - factory"` (wrong case), to test normalized matching.

5. **Column headers** must match our existing Work Order field mapping:
   - `production_item`, `bom_no`, `qty`, `company`, `wip_warehouse`, `fg_warehouse`, `planned_start_date` (optional), `name` or work order id column if used

6. **Do not include** warehouses/items/customers that need to be created from scratch — Pass 2.5 resolves names; it does not create complex master data like new Warehouses.

7. Output: one CSV file named `work_orders_link_resolution_test.csv` plus a 1-paragraph note explaining which rows test which resolution scenario.

---

## My recommendation

| Approach | When to use |
|---|---|
| **Re-run Phase C on existing session** | Start here — zero new data, tests the exact failure you hit |
| **Add 2–3 supplemental Work Order rows** | If you want a clean before/after without re-touching other transactional doctypes |
| **Full new dummy dataset** | Not needed — overkill for this change |
| **`--dry-run`** | Not useful here — Pass 2.5 is skipped in dry-run mode |

**Suggested order:**
1. Re-run Phase C via `is_harness` on green-surface (live, not dry-run)
2. Confirm Pass 2.5 logs + `resolution_summary` + Work Orders in ERPNext
3. Only if you want extra proof, add the small supplemental CSV from the prompt above

If you want, switch to Agent mode and I can help you run the harness command and interpret the output.

---

**User**

PS C:\dev\F3Next> python -m containers.implementation.is_harness --step execute_import_phase --phase phase_c_transactional
15:57:38  INFO      is_harness  │
15:57:38  INFO      is_harness  │  ════════════════════════════════════════════════════════════════════════
15:57:38  INFO      is_harness  │    IS STEP HARNESS
15:57:38  INFO      is_harness  │    step     : execute_import_phase
15:57:38  INFO      is_harness  │    mock_llm : False
15:57:38  INFO      is_harness  │    dry_run  : False
15:57:38  INFO      is_harness  │  ════════════════════════════════════════════════════════════════════════
15:57:38  INFO      is_harness  │
15:57:39  INFO      is_harness  │    Fixture  : C:\dev\F3Next\containers\implementation\dev_fixtures\execute_import_phase.json
15:57:39  INFO      is_harness  │    Input    : {"_comment": "Executes one import phase against ERPNext. Use --dry-run to skip actual API writes. Requires build_import_plan to have run first for this session.", "session_id": "3145be35-2991-48dd-b43...
15:57:39  INFO      is_harness  │
15:57:39  INFO      is_harness.activity  │  ▶ execute_import_phase started | session=3145be35-2991-48dd-b43e-e59df9e86f5c phase=phase_c_transactional dry_run=True
15:57:46  INFO      is_harness.activity  │    🔑 Auto-resolved base_url from Project.deployment_details: https://green-surface.f3next.in
15:57:46  INFO      is_harness.activity  │    🔑 Auto-resolved API credentials from Project.deployment_details
15:57:46  INFO      is_harness.activity  │    🌱  PRE-FLIGHT SEEDER — dry_run mode, skipping 1 seed step(s)
15:57:46  INFO      is_harness.activity  │
15:57:46  INFO      is_harness.activity  │
15:57:46  WARNING   is_harness.activity  │    ⚠️  DATA GAP: Sales Order has no mapped data file and no baseline — skipping
15:57:46  WARNING   is_harness.activity  │    ⚠️  DATA GAP: Delivery Note has no mapped data file and no baseline — skipping
15:57:46  WARNING   is_harness.activity  │    ⚠️  DATA GAP: Work Order has no mapped data file and no baseline — skipping
15:57:46  WARNING   is_harness.activity  │    ⚠️  DATA GAP: Sales Invoice has no mapped data file and no baseline — skipping
15:57:46  WARNING   is_harness.activity  │    ⚠️  DATA GAP: BOM (Formulation) has no mapped data file and no baseline — skipping
15:57:46  WARNING   is_harness.activity  │    ⚠️  DATA GAP: Batch has no mapped data file and no baseline — skipping
15:57:46  WARNING   is_harness.activity  │    ⚠️  DATA GAP: Branch has no mapped data file and no baseline — skipping
15:57:46  WARNING   is_harness.activity  │    ⚠️  DATA GAP: Customer or Lead has no mapped data file and no baseline — skipping
15:57:46  WARNING   is_harness.activity  │    ⚠️  DATA GAP: Department has no mapped data file and no baseline — skipping
15:57:46  WARNING   is_harness.activity  │    ⚠️  DATA GAP: Designation has no mapped data file and no baseline — skipping
15:57:46  WARNING   is_harness.activity  │    ⚠️  DATA GAP: DocType has no mapped data file and no baseline — skipping
15:57:46  WARNING   is_harness.activity  │    ⚠️  DATA GAP: Employee has no mapped data file and no baseline — skipping
15:57:46  WARNING   is_harness.activity  │    ⚠️  DATA GAP: Gender has no mapped data file and no baseline — skipping
15:57:46  WARNING   is_harness.activity  │    ⚠️  DATA GAP: Holiday List has no mapped data file and no baseline — skipping
15:57:46  WARNING   is_harness.activity  │    ⚠️  DATA GAP: Issue has no mapped data file and no baseline — skipping
15:57:46  WARNING   is_harness.activity  │    ⚠️  DATA GAP: Item Attribute has no mapped data file and no baseline — skipping
15:57:46  WARNING   is_harness.activity  │    ⚠️  DATA GAP: Item Variant has no mapped data file and no baseline — skipping
15:57:46  WARNING   is_harness.activity  │    ⚠️  DATA GAP: Job Card has no mapped data file and no baseline — skipping
15:57:46  WARNING   is_harness.activity  │    ⚠️  DATA GAP: Letter Head has no mapped data file and no baseline — skipping
15:57:46  WARNING   is_harness.activity  │    ⚠️  DATA GAP: Operation has no mapped data file and no baseline — skipping
15:57:46  WARNING   is_harness.activity  │    ⚠️  DATA GAP: Plant Floor has no mapped data file and no baseline — skipping
15:57:46  WARNING   is_harness.activity  │    ⚠️  DATA GAP: Project Type has no mapped data file and no baseline — skipping
15:57:46  WARNING   is_harness.activity  │    ⚠️  DATA GAP: Quality Inspection has no mapped data file and no baseline — skipping
15:57:46  WARNING   is_harness.activity  │    ⚠️  DATA GAP: Quality Inspection Template has no mapped data file and no baseline — skipping
15:57:46  WARNING   is_harness.activity  │    ⚠️  DATA GAP: Quotation has no mapped data file and no baseline — skipping
15:57:46  WARNING   is_harness.activity  │    ⚠️  DATA GAP: Salutation has no mapped data file and no baseline — skipping
15:57:46  WARNING   is_harness.activity  │    ⚠️  DATA GAP: Serial No has no mapped data file and no baseline — skipping
15:57:46  WARNING   is_harness.activity  │    ⚠️  DATA GAP: Stock Entry (Issue, Transfer, Manufacture) has no mapped data file and no baseline — skipping
15:57:46  WARNING   is_harness.activity  │    ⚠️  DATA GAP: Task Type has no mapped data file and no baseline — skipping
15:57:46  WARNING   is_harness.activity  │    ⚠️  DATA GAP: User has no mapped data file and no baseline — skipping
15:57:46  WARNING   is_harness.activity  │    ⚠️  DATA GAP: Work Order (Batch Ticket) has no mapped data file and no baseline — skipping
15:57:46  WARNING   is_harness.activity  │    ⚠️  DATA GAP: Workstation has no mapped data file and no baseline — skipping
15:57:46  WARNING   is_harness.activity  │    ⚠️  DATA GAP: Workstation Type has no mapped data file and no baseline — skipping
15:57:47  INFO      is_harness.activity  │  ✅ execute_import_phase done | phase=phase_c_transactional records=0
15:57:47  INFO      is_harness  │
15:57:47  INFO      is_harness  │  ════════════════════════════════════════════════════════════════════════
15:57:47  INFO      is_harness  │    ✅  STEP COMPLETE: execute_import_phase
15:57:47  INFO      is_harness  │  ════════════════════════════════════════════════════════════════════════
15:57:47  INFO      is_harness  │

{
  "phase": "phase_c_transactional",
  "status": "success",
  "steps_completed": 0,
  "steps_failed": 0,
  "records_created": 0,
  "execution_logs": []
}

PS C:\dev\F3Next>

---

**Cursor**

Your run skipped everything — I'll trace why (dry_run flag and the import plan's data gaps) so we can get a real Phase C test.


Your run did not actually test Pass 2.5. Two separate issues blocked it:

## What went wrong

### 1. It ran in dry-run mode (despite the banner saying `False`)

The harness banner shows the **CLI flag** (`args.dry_run`), not what the activity actually received.

Your fixture [`execute_import_phase.json`](containers/implementation/dev_fixtures/execute_import_phase.json) has:

```json
"dry_run": true
```

The harness only **forces dry-run ON** when you pass `--dry-run`; it never forces it OFF. So the activity log correctly shows:

```
dry_run=True
```

That means:
- Pass 2.5 was **skipped** (only runs when `not dry_run`)
- Pass 1 seeder was skipped
- Main loop mocked success without touching ERPNext

### 2. Every step was `data_gap` — nothing to import

All Phase C steps were skipped because the import plan in Supabase has `action: "data_gap"` for them, not `action: "create"` with an R2 path.

That happens when `finalize_import_plan` either:
- never ran after mapping, or
- ran but found **no matching row in `ISMappedData`** for those doctype names (e.g. plan says `"Work Order (Batch Ticket)"` but mapped data is stored as `"Work Order"`)

So Pass 2.5 had **zero rows to scan** even if dry-run had been off.

---

## How to fix and re-test

### Step 1 — Turn off dry-run in the fixture

Edit `containers/implementation/dev_fixtures/execute_import_phase.json`:

```json
"dry_run": false
```

(Or create a copy like `execute_import_phase_live.json` and pass `--fixture` to that file.)

### Step 2 — Finalize the import plan first

This wires mapped R2 paths from `ISMappedData` into the plan:

```powershell
python -m containers.implementation.is_harness --step finalize_import_plan
```

Check the output — you want `"status": "ready"`, not `"blocked"`.

### Step 3 — Verify mapped data exists (Supabase)

Run in Supabase SQL editor:

```sql
-- Mapped files for this session
SELECT target_doctype, total_rows, mapped_payload_r2_path, validation_status
FROM is_mapped_data
WHERE session_id = '3145be35-2991-48dd-b43e-e59df9e86f5c'
ORDER BY target_doctype;

-- What the import plan actually says for Phase C
SELECT phases->'phase_c_transactional'->'steps'
FROM is_import_plans
WHERE session_id = '3145be35-2991-48dd-b43e-e59df9e86f5c'
ORDER BY created_at DESC
LIMIT 1;
```

You need at least one step with:
- `"action": "create"`
- `"data_source": "<actual R2 path>"` (not `"none"` or `"pending_mapping"`)

If `is_mapped_data` has Work Order rows but the plan still shows `data_gap`, the **doctype name mismatch** is the likely cause — plan doctype must exactly match `target_doctype` in `is_mapped_data`.

### Step 4 — Re-run Phase C live

```powershell
python -m containers.implementation.is_harness --step execute_import_phase --phase phase_c_transactional
```

**Success looks like:**

```
🔗  PASS 2.5 — Bulk link pre-resolution
BulkLinkResolver: Warehouse 'WIP - Factory' -> 'WIP - GS'
```

And `execution_logs` should be non-empty with `resolution_summary`.

---

## If Step 2/3 still shows all data gaps

Your harness session may not be the same state as when the original failure happened. Options:

| Option | Effort | Best for |
|---|---|---|
| **Re-trigger import via UI** (sandbox approve / Phase C again on the live Temporal worker) | Low | Testing the real path that failed before |
| **Re-run mapping + finalize** on the same session | Medium | If `is_mapped_data` is empty |
| **Add 2–3 new Work Order CSV rows** + upload + map + finalize | Medium | Clean isolated proof |
| **Quick sanity check only** — test resolver in isolation | Lowest | Confirm logic works without full pipeline |

Quick isolated test (no DB needed):

```powershell
python -c "from shared.erp_adapters.link_resolver import resolve_single; print(resolve_single('WIP - Factory', ['WIP - GS', 'Stores - GS']))"
```

Expected: `resolved='WIP - GS'`

---

## My recommendation for you right now

1. Set `"dry_run": false` in the fixture  
2. Run `finalize_import_plan`  
3. Check Supabase — confirm Work Order has `action: create` + R2 path  
4. Re-run Phase C  

If Supabase shows no mapped Work Order data for that session, **don't fight the harness** — either re-upload the Work Order CSV through the UI and re-run Phase C via Temporal, or use the supplemental CSV prompt from my earlier message to create 2–3 fresh test rows.

I'm in Ask mode so I can't edit the fixture or run commands for you. Switch to Agent mode if you want me to fix the fixture and walk through the Supabase checks interactively.

---

**User**

PS C:\dev\F3Next> python -m containers.implementation.is_harness --step finalize_import_plan
16:06:36  INFO      is_harness  │
16:06:36  INFO      is_harness  │  ════════════════════════════════════════════════════════════════════════
16:06:36  INFO      is_harness  │    IS STEP HARNESS
16:06:36  INFO      is_harness  │    step     : finalize_import_plan
16:06:36  INFO      is_harness  │    mock_llm : False
16:06:36  INFO      is_harness  │    dry_run  : False
16:06:36  INFO      is_harness  │  ════════════════════════════════════════════════════════════════════════
16:06:36  INFO      is_harness  │
16:06:37  INFO      is_harness  │    Fixture  : C:\dev\F3Next\containers\implementation\dev_fixtures\finalize_import_plan.json
16:06:37  INFO      is_harness  │    Input    : {"_comment": "Finalizes import plan using actual mapping locations and validation checks.", "session_id": "3145be35-2991-48dd-b43e-e59df9e86f5c", "project_id": "b6ff0b7f-a616-4179-8f68-deda9b3578af", ...
16:06:37  INFO      is_harness  │
16:06:38  INFO      is_harness.activity  │  ▶ finalize_import_plan started | session=3145be35-2991-48dd-b43e-e59df9e86f5c
16:06:44  INFO      is_harness.activity  │    ✅ Finalized R2 plan uploaded.
16:06:44  INFO      is_harness.activity  │    ✅ Finalized ISImportPlan database record updated | id=721f27cc-8b37-4471-ac59-f1b08a924d1a status=ready
16:06:44  INFO      is_harness  │
16:06:44  INFO      is_harness  │  ════════════════════════════════════════════════════════════════════════
16:06:44  INFO      is_harness  │    ✅  STEP COMPLETE: finalize_import_plan
16:06:44  INFO      is_harness  │  ════════════════════════════════════════════════════════════════════════
16:06:44  INFO      is_harness  │

"ready"

PS C:\dev\F3Next> python -m containers.implementation.is_harness --step execute_import_phase --phase phase_c_transactional
16:08:34  INFO      is_harness  │
16:08:34  INFO      is_harness  │  ════════════════════════════════════════════════════════════════════════
16:08:34  INFO      is_harness  │    IS STEP HARNESS
16:08:34  INFO      is_harness  │    step     : execute_import_phase
16:08:34  INFO      is_harness  │    mock_llm : False
16:08:34  INFO      is_harness  │    dry_run  : False
16:08:34  INFO      is_harness  │  ════════════════════════════════════════════════════════════════════════
16:08:34  INFO      is_harness  │
16:08:36  INFO      is_harness  │    Fixture  : C:\dev\F3Next\containers\implementation\dev_fixtures\execute_import_phase.json
16:08:36  INFO      is_harness  │    Input    : {"_comment": "Executes one import phase against ERPNext. Use --dry-run to skip actual API writes. Requires build_import_plan to have run first for this session.", "session_id": "3145be35-2991-48dd-b43...
16:08:36  INFO      is_harness  │
16:08:37  INFO      is_harness.activity  │  ▶ execute_import_phase started | session=3145be35-2991-48dd-b43e-e59df9e86f5c phase=phase_c_transactional dry_run=False
16:08:42  INFO      is_harness.activity  │    🔑 Auto-resolved base_url from Project.deployment_details: https://green-surface.f3next.in
16:08:42  INFO      is_harness.activity  │    🔑 Auto-resolved API credentials from Project.deployment_details
16:08:42  INFO      is_harness.activity  │
16:08:42  INFO      is_harness.activity  │    🌱  PRE-FLIGHT SEEDER — seeding 1 baseline doctype(s)
16:08:42  INFO      shared.erp_adapters.erpnext  │  ERPNextAdapter.get_doctype_schema: fetching live schema for Currency
16:08:43  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/DocType/Currency "HTTP/1.1 200 OK"
16:08:43  INFO      shared.erp_adapters.erpnext  │  ERPNextAdapter.get_doctype_schema: Currency → 8 fields
16:08:43  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22INR%22%5D%5D "HTTP/1.1 200 OK"
16:08:43  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22INR%22%5D%5D "HTTP/1.1 200 OK"
16:08:43  INFO      shared.erp_adapters.erpnext  │  Record Currency 'INR' already exists — skipping creation
16:08:43  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22AED%22%5D%5D "HTTP/1.1 200 OK"
16:08:43  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22AED%22%5D%5D "HTTP/1.1 200 OK"
16:08:43  INFO      shared.erp_adapters.erpnext  │  Record Currency 'AED' already exists — skipping creation
16:08:44  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22AUD%22%5D%5D "HTTP/1.1 200 OK"
16:08:44  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22AUD%22%5D%5D "HTTP/1.1 200 OK"
16:08:44  INFO      shared.erp_adapters.erpnext  │  Record Currency 'AUD' already exists — skipping creation
16:08:44  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22CHF%22%5D%5D "HTTP/1.1 200 OK"
16:08:44  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22CHF%22%5D%5D "HTTP/1.1 200 OK"
16:08:44  INFO      shared.erp_adapters.erpnext  │  Record Currency 'CHF' already exists — skipping creation
16:08:44  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22CNY%22%5D%5D "HTTP/1.1 200 OK"
16:08:44  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22CNY%22%5D%5D "HTTP/1.1 200 OK"
16:08:44  INFO      shared.erp_adapters.erpnext  │  Record Currency 'CNY' already exists — skipping creation
16:08:45  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22EUR%22%5D%5D "HTTP/1.1 200 OK"
16:08:45  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22EUR%22%5D%5D "HTTP/1.1 200 OK"
16:08:45  INFO      shared.erp_adapters.erpnext  │  Record Currency 'EUR' already exists — skipping creation
16:08:45  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22GBP%22%5D%5D "HTTP/1.1 200 OK"
16:08:45  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22GBP%22%5D%5D "HTTP/1.1 200 OK"
16:08:45  INFO      shared.erp_adapters.erpnext  │  Record Currency 'GBP' already exists — skipping creation
16:08:45  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22JPY%22%5D%5D "HTTP/1.1 200 OK"
16:08:45  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22JPY%22%5D%5D "HTTP/1.1 200 OK"
16:08:45  INFO      shared.erp_adapters.erpnext  │  Record Currency 'JPY' already exists — skipping creation
16:08:46  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22USD%22%5D%5D "HTTP/1.1 200 OK"
16:08:46  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22USD%22%5D%5D "HTTP/1.1 200 OK"
16:08:46  INFO      shared.erp_adapters.erpnext  │  Record Currency 'USD' already exists — skipping creation
16:08:46  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22ZWL%22%5D%5D "HTTP/1.1 200 OK"
16:08:46  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22ZWL%22%5D%5D "HTTP/1.1 200 OK"
16:08:46  INFO      shared.erp_adapters.erpnext  │  Record Currency 'ZWL' already exists — skipping creation
16:08:46  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22ZMW%22%5D%5D "HTTP/1.1 200 OK"
16:08:46  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22ZMW%22%5D%5D "HTTP/1.1 200 OK"
16:08:46  INFO      shared.erp_adapters.erpnext  │  Record Currency 'ZMW' already exists — skipping creation
16:08:46  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22YER%22%5D%5D "HTTP/1.1 200 OK"
16:08:47  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22YER%22%5D%5D "HTTP/1.1 200 OK"
16:08:47  INFO      shared.erp_adapters.erpnext  │  Record Currency 'YER' already exists — skipping creation
16:08:47  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22VND%22%5D%5D "HTTP/1.1 200 OK"
16:08:47  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22VND%22%5D%5D "HTTP/1.1 200 OK"
16:08:47  INFO      shared.erp_adapters.erpnext  │  Record Currency 'VND' already exists — skipping creation
16:08:47  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22VEF%22%5D%5D "HTTP/1.1 200 OK"
16:08:47  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22VEF%22%5D%5D "HTTP/1.1 200 OK"
16:08:47  INFO      shared.erp_adapters.erpnext  │  Record Currency 'VEF' already exists — skipping creation
16:08:48  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22VUV%22%5D%5D "HTTP/1.1 200 OK"
16:08:48  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22VUV%22%5D%5D "HTTP/1.1 200 OK"
16:08:48  INFO      shared.erp_adapters.erpnext  │  Record Currency 'VUV' already exists — skipping creation
16:08:48  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22UZS%22%5D%5D "HTTP/1.1 200 OK"
16:08:48  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22UZS%22%5D%5D "HTTP/1.1 200 OK"
16:08:48  INFO      shared.erp_adapters.erpnext  │  Record Currency 'UZS' already exists — skipping creation
16:08:48  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22UYU%22%5D%5D "HTTP/1.1 200 OK"
16:08:48  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22UYU%22%5D%5D "HTTP/1.1 200 OK"
16:08:48  INFO      shared.erp_adapters.erpnext  │  Record Currency 'UYU' already exists — skipping creation
16:08:49  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22UAH%22%5D%5D "HTTP/1.1 200 OK"
16:08:49  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22UAH%22%5D%5D "HTTP/1.1 200 OK"
16:08:49  INFO      shared.erp_adapters.erpnext  │  Record Currency 'UAH' already exists — skipping creation
16:08:49  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22UGX%22%5D%5D "HTTP/1.1 200 OK"
16:08:49  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22UGX%22%5D%5D "HTTP/1.1 200 OK"
16:08:49  INFO      shared.erp_adapters.erpnext  │  Record Currency 'UGX' already exists — skipping creation
16:08:49  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22TMM%22%5D%5D "HTTP/1.1 200 OK"
16:08:49  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22TMM%22%5D%5D "HTTP/1.1 200 OK"
16:08:49  INFO      shared.erp_adapters.erpnext  │  Record Currency 'TMM' already exists — skipping creation
16:08:50  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22TRY%22%5D%5D "HTTP/1.1 200 OK"
16:08:50  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22TRY%22%5D%5D "HTTP/1.1 200 OK"
16:08:50  INFO      shared.erp_adapters.erpnext  │  Record Currency 'TRY' already exists — skipping creation
16:08:50  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22TND%22%5D%5D "HTTP/1.1 200 OK"
16:08:50  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22TND%22%5D%5D "HTTP/1.1 200 OK"
16:08:50  INFO      shared.erp_adapters.erpnext  │  Record Currency 'TND' already exists — skipping creation
16:08:50  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22TTD%22%5D%5D "HTTP/1.1 200 OK"
16:08:50  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22TTD%22%5D%5D "HTTP/1.1 200 OK"
16:08:50  INFO      shared.erp_adapters.erpnext  │  Record Currency 'TTD' already exists — skipping creation
16:08:51  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22TOP%22%5D%5D "HTTP/1.1 200 OK"
16:08:51  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22TOP%22%5D%5D "HTTP/1.1 200 OK"
16:08:51  INFO      shared.erp_adapters.erpnext  │  Record Currency 'TOP' already exists — skipping creation
16:08:51  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22THB%22%5D%5D "HTTP/1.1 200 OK"
16:08:51  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22THB%22%5D%5D "HTTP/1.1 200 OK"
16:08:51  INFO      shared.erp_adapters.erpnext  │  Record Currency 'THB' already exists — skipping creation
16:08:51  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22TZS%22%5D%5D "HTTP/1.1 200 OK"
16:08:51  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22TZS%22%5D%5D "HTTP/1.1 200 OK"
16:08:51  INFO      shared.erp_adapters.erpnext  │  Record Currency 'TZS' already exists — skipping creation
16:08:52  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22TWD%22%5D%5D "HTTP/1.1 200 OK"
16:08:52  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22TWD%22%5D%5D "HTTP/1.1 200 OK"
16:08:52  INFO      shared.erp_adapters.erpnext  │  Record Currency 'TWD' already exists — skipping creation
16:08:52  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22SYP%22%5D%5D "HTTP/1.1 200 OK"
16:08:52  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22SYP%22%5D%5D "HTTP/1.1 200 OK"
16:08:52  INFO      shared.erp_adapters.erpnext  │  Record Currency 'SYP' already exists — skipping creation
16:08:52  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22SEK%22%5D%5D "HTTP/1.1 200 OK"
16:08:52  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22SEK%22%5D%5D "HTTP/1.1 200 OK"
16:08:52  INFO      shared.erp_adapters.erpnext  │  Record Currency 'SEK' already exists — skipping creation
16:08:53  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22SZL%22%5D%5D "HTTP/1.1 200 OK"
16:08:53  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22SZL%22%5D%5D "HTTP/1.1 200 OK"
16:08:53  INFO      shared.erp_adapters.erpnext  │  Record Currency 'SZL' already exists — skipping creation
16:08:53  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22SRD%22%5D%5D "HTTP/1.1 200 OK"
16:08:53  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22SRD%22%5D%5D "HTTP/1.1 200 OK"
16:08:53  INFO      shared.erp_adapters.erpnext  │  Record Currency 'SRD' already exists — skipping creation
16:08:53  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22SDG%22%5D%5D "HTTP/1.1 200 OK"
16:08:53  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22SDG%22%5D%5D "HTTP/1.1 200 OK"
16:08:53  INFO      shared.erp_adapters.erpnext  │  Record Currency 'SDG' already exists — skipping creation
16:08:54  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22LKR%22%5D%5D "HTTP/1.1 200 OK"
16:08:54  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22LKR%22%5D%5D "HTTP/1.1 200 OK"
16:08:54  INFO      shared.erp_adapters.erpnext  │  Record Currency 'LKR' already exists — skipping creation
16:08:54  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22ZAR%22%5D%5D "HTTP/1.1 200 OK"
16:08:54  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22ZAR%22%5D%5D "HTTP/1.1 200 OK"
16:08:54  INFO      shared.erp_adapters.erpnext  │  Record Currency 'ZAR' already exists — skipping creation
16:08:54  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22SOS%22%5D%5D "HTTP/1.1 200 OK"
16:08:54  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22SOS%22%5D%5D "HTTP/1.1 200 OK"
16:08:54  INFO      shared.erp_adapters.erpnext  │  Record Currency 'SOS' already exists — skipping creation
16:08:55  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22SBD%22%5D%5D "HTTP/1.1 200 OK"
16:08:55  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22SBD%22%5D%5D "HTTP/1.1 200 OK"
16:08:55  INFO      shared.erp_adapters.erpnext  │  Record Currency 'SBD' already exists — skipping creation
16:08:55  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22SGD%22%5D%5D "HTTP/1.1 200 OK"
16:08:55  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22SGD%22%5D%5D "HTTP/1.1 200 OK"
16:08:55  INFO      shared.erp_adapters.erpnext  │  Record Currency 'SGD' already exists — skipping creation
16:08:55  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22SLL%22%5D%5D "HTTP/1.1 200 OK"
16:08:55  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22SLL%22%5D%5D "HTTP/1.1 200 OK"
16:08:55  INFO      shared.erp_adapters.erpnext  │  Record Currency 'SLL' already exists — skipping creation
16:08:56  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22SCR%22%5D%5D "HTTP/1.1 200 OK"
16:08:56  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22SCR%22%5D%5D "HTTP/1.1 200 OK"
16:08:56  INFO      shared.erp_adapters.erpnext  │  Record Currency 'SCR' already exists — skipping creation
16:08:56  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22RSD%22%5D%5D "HTTP/1.1 200 OK"
16:08:56  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22RSD%22%5D%5D "HTTP/1.1 200 OK"
16:08:56  INFO      shared.erp_adapters.erpnext  │  Record Currency 'RSD' already exists — skipping creation
16:08:56  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22SAR%22%5D%5D "HTTP/1.1 200 OK"
16:08:56  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22SAR%22%5D%5D "HTTP/1.1 200 OK"
16:08:56  INFO      shared.erp_adapters.erpnext  │  Record Currency 'SAR' already exists — skipping creation
16:08:57  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22STD%22%5D%5D "HTTP/1.1 200 OK"
16:08:57  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22STD%22%5D%5D "HTTP/1.1 200 OK"
16:08:57  INFO      shared.erp_adapters.erpnext  │  Record Currency 'STD' already exists — skipping creation
16:08:57  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22WST%22%5D%5D "HTTP/1.1 200 OK"
16:08:57  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22WST%22%5D%5D "HTTP/1.1 200 OK"
16:08:57  INFO      shared.erp_adapters.erpnext  │  Record Currency 'WST' already exists — skipping creation
16:08:57  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22SHP%22%5D%5D "HTTP/1.1 200 OK"
16:08:57  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22SHP%22%5D%5D "HTTP/1.1 200 OK"
16:08:57  INFO      shared.erp_adapters.erpnext  │  Record Currency 'SHP' already exists — skipping creation
16:08:58  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22RWF%22%5D%5D "HTTP/1.1 200 OK"
16:08:58  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22RWF%22%5D%5D "HTTP/1.1 200 OK"
16:08:58  INFO      shared.erp_adapters.erpnext  │  Record Currency 'RWF' already exists — skipping creation
16:08:58  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22RUB%22%5D%5D "HTTP/1.1 200 OK"
16:08:58  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22RUB%22%5D%5D "HTTP/1.1 200 OK"
16:08:58  INFO      shared.erp_adapters.erpnext  │  Record Currency 'RUB' already exists — skipping creation
16:08:58  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22RON%22%5D%5D "HTTP/1.1 200 OK"
16:08:58  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22RON%22%5D%5D "HTTP/1.1 200 OK"
16:08:58  INFO      shared.erp_adapters.erpnext  │  Record Currency 'RON' already exists — skipping creation
16:08:59  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22QAR%22%5D%5D "HTTP/1.1 200 OK"
16:08:59  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22QAR%22%5D%5D "HTTP/1.1 200 OK"
16:08:59  INFO      shared.erp_adapters.erpnext  │  Record Currency 'QAR' already exists — skipping creation
16:08:59  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22PLN%22%5D%5D "HTTP/1.1 200 OK"
16:08:59  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22PLN%22%5D%5D "HTTP/1.1 200 OK"
16:08:59  INFO      shared.erp_adapters.erpnext  │  Record Currency 'PLN' already exists — skipping creation
16:08:59  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22PHP%22%5D%5D "HTTP/1.1 200 OK"
16:09:00  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22PHP%22%5D%5D "HTTP/1.1 200 OK"
16:09:00  INFO      shared.erp_adapters.erpnext  │  Record Currency 'PHP' already exists — skipping creation
16:09:00  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22PEN%22%5D%5D "HTTP/1.1 200 OK"
16:09:00  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22PEN%22%5D%5D "HTTP/1.1 200 OK"
16:09:00  INFO      shared.erp_adapters.erpnext  │  Record Currency 'PEN' already exists — skipping creation
16:09:00  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22PYG%22%5D%5D "HTTP/1.1 200 OK"
16:09:00  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22PYG%22%5D%5D "HTTP/1.1 200 OK"
16:09:00  INFO      shared.erp_adapters.erpnext  │  Record Currency 'PYG' already exists — skipping creation
16:09:01  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22PGK%22%5D%5D "HTTP/1.1 200 OK"
16:09:01  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22PGK%22%5D%5D "HTTP/1.1 200 OK"
16:09:01  INFO      shared.erp_adapters.erpnext  │  Record Currency 'PGK' already exists — skipping creation
16:09:01  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22PKR%22%5D%5D "HTTP/1.1 200 OK"
16:09:02  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22PKR%22%5D%5D "HTTP/1.1 200 OK"
16:09:02  INFO      shared.erp_adapters.erpnext  │  Record Currency 'PKR' already exists — skipping creation
16:09:03  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22OMR%22%5D%5D "HTTP/1.1 200 OK"
16:09:03  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22OMR%22%5D%5D "HTTP/1.1 200 OK"
16:09:03  INFO      shared.erp_adapters.erpnext  │  Record Currency 'OMR' already exists — skipping creation
16:09:04  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22NOK%22%5D%5D "HTTP/1.1 200 OK"
16:09:04  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22NOK%22%5D%5D "HTTP/1.1 200 OK"
16:09:04  INFO      shared.erp_adapters.erpnext  │  Record Currency 'NOK' already exists — skipping creation
16:09:04  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22NGN%22%5D%5D "HTTP/1.1 200 OK"
16:09:04  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22NGN%22%5D%5D "HTTP/1.1 200 OK"
16:09:04  INFO      shared.erp_adapters.erpnext  │  Record Currency 'NGN' already exists — skipping creation
16:09:04  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22NIO%22%5D%5D "HTTP/1.1 200 OK"
16:09:04  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22NIO%22%5D%5D "HTTP/1.1 200 OK"
16:09:04  INFO      shared.erp_adapters.erpnext  │  Record Currency 'NIO' already exists — skipping creation
16:09:05  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22NZD%22%5D%5D "HTTP/1.1 200 OK"
16:09:05  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22NZD%22%5D%5D "HTTP/1.1 200 OK"
16:09:05  INFO      shared.erp_adapters.erpnext  │  Record Currency 'NZD' already exists — skipping creation
16:09:05  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22NPR%22%5D%5D "HTTP/1.1 200 OK"
16:09:05  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22NPR%22%5D%5D "HTTP/1.1 200 OK"
16:09:05  INFO      shared.erp_adapters.erpnext  │  Record Currency 'NPR' already exists — skipping creation
16:09:05  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22NAD%22%5D%5D "HTTP/1.1 200 OK"
16:09:05  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22NAD%22%5D%5D "HTTP/1.1 200 OK"
16:09:05  INFO      shared.erp_adapters.erpnext  │  Record Currency 'NAD' already exists — skipping creation
16:09:06  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22MMK%22%5D%5D "HTTP/1.1 200 OK"
16:09:06  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22MMK%22%5D%5D "HTTP/1.1 200 OK"
16:09:06  INFO      shared.erp_adapters.erpnext  │  Record Currency 'MMK' already exists — skipping creation
16:09:06  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22MZN%22%5D%5D "HTTP/1.1 200 OK"
16:09:06  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22MZN%22%5D%5D "HTTP/1.1 200 OK"
16:09:06  INFO      shared.erp_adapters.erpnext  │  Record Currency 'MZN' already exists — skipping creation
16:09:06  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22MAD%22%5D%5D "HTTP/1.1 200 OK"
16:09:06  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22MAD%22%5D%5D "HTTP/1.1 200 OK"
16:09:06  INFO      shared.erp_adapters.erpnext  │  Record Currency 'MAD' already exists — skipping creation
16:09:07  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22MNT%22%5D%5D "HTTP/1.1 200 OK"
16:09:07  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22MNT%22%5D%5D "HTTP/1.1 200 OK"
16:09:07  INFO      shared.erp_adapters.erpnext  │  Record Currency 'MNT' already exists — skipping creation
16:09:07  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22MDL%22%5D%5D "HTTP/1.1 200 OK"
16:09:07  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22MDL%22%5D%5D "HTTP/1.1 200 OK"
16:09:07  INFO      shared.erp_adapters.erpnext  │  Record Currency 'MDL' already exists — skipping creation
16:09:07  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22MXN%22%5D%5D "HTTP/1.1 200 OK"
16:09:07  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22MXN%22%5D%5D "HTTP/1.1 200 OK"
16:09:07  INFO      shared.erp_adapters.erpnext  │  Record Currency 'MXN' already exists — skipping creation
16:09:08  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22MUR%22%5D%5D "HTTP/1.1 200 OK"
16:09:08  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22MUR%22%5D%5D "HTTP/1.1 200 OK"
16:09:08  INFO      shared.erp_adapters.erpnext  │  Record Currency 'MUR' already exists — skipping creation
16:09:08  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22MRO%22%5D%5D "HTTP/1.1 200 OK"
16:09:08  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22MRO%22%5D%5D "HTTP/1.1 200 OK"
16:09:08  INFO      shared.erp_adapters.erpnext  │  Record Currency 'MRO' already exists — skipping creation
16:09:08  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22MVR%22%5D%5D "HTTP/1.1 200 OK"
16:09:08  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22MVR%22%5D%5D "HTTP/1.1 200 OK"
16:09:08  INFO      shared.erp_adapters.erpnext  │  Record Currency 'MVR' already exists — skipping creation
16:09:09  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22MYR%22%5D%5D "HTTP/1.1 200 OK"
16:09:09  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22MYR%22%5D%5D "HTTP/1.1 200 OK"
16:09:09  INFO      shared.erp_adapters.erpnext  │  Record Currency 'MYR' already exists — skipping creation
16:09:09  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22MWK%22%5D%5D "HTTP/1.1 200 OK"
16:09:09  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22MWK%22%5D%5D "HTTP/1.1 200 OK"
16:09:09  INFO      shared.erp_adapters.erpnext  │  Record Currency 'MWK' already exists — skipping creation
16:09:09  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22MKD%22%5D%5D "HTTP/1.1 200 OK"
16:09:09  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22MKD%22%5D%5D "HTTP/1.1 200 OK"
16:09:09  INFO      shared.erp_adapters.erpnext  │  Record Currency 'MKD' already exists — skipping creation
16:09:09  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22MOP%22%5D%5D "HTTP/1.1 200 OK"
16:09:10  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22MOP%22%5D%5D "HTTP/1.1 200 OK"
16:09:10  INFO      shared.erp_adapters.erpnext  │  Record Currency 'MOP' already exists — skipping creation
16:09:10  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22LTL%22%5D%5D "HTTP/1.1 200 OK"
16:09:10  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22LTL%22%5D%5D "HTTP/1.1 200 OK"
16:09:10  INFO      shared.erp_adapters.erpnext  │  Record Currency 'LTL' already exists — skipping creation
16:09:10  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22LYD%22%5D%5D "HTTP/1.1 200 OK"
16:09:10  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22LYD%22%5D%5D "HTTP/1.1 200 OK"
16:09:10  INFO      shared.erp_adapters.erpnext  │  Record Currency 'LYD' already exists — skipping creation
16:09:10  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22LRD%22%5D%5D "HTTP/1.1 200 OK"
16:09:11  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22LRD%22%5D%5D "HTTP/1.1 200 OK"
16:09:11  INFO      shared.erp_adapters.erpnext  │  Record Currency 'LRD' already exists — skipping creation
16:09:11  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22LSL%22%5D%5D "HTTP/1.1 200 OK"
16:09:11  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22LSL%22%5D%5D "HTTP/1.1 200 OK"
16:09:11  INFO      shared.erp_adapters.erpnext  │  Record Currency 'LSL' already exists — skipping creation
16:09:11  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22LBP%22%5D%5D "HTTP/1.1 200 OK"
16:09:11  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22LBP%22%5D%5D "HTTP/1.1 200 OK"
16:09:11  INFO      shared.erp_adapters.erpnext  │  Record Currency 'LBP' already exists — skipping creation
16:09:11  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22LVL%22%5D%5D "HTTP/1.1 200 OK"
16:09:12  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22LVL%22%5D%5D "HTTP/1.1 200 OK"
16:09:12  INFO      shared.erp_adapters.erpnext  │  Record Currency 'LVL' already exists — skipping creation
16:09:12  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22LAK%22%5D%5D "HTTP/1.1 200 OK"
16:09:12  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22LAK%22%5D%5D "HTTP/1.1 200 OK"
16:09:12  INFO      shared.erp_adapters.erpnext  │  Record Currency 'LAK' already exists — skipping creation
16:09:12  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22KGS%22%5D%5D "HTTP/1.1 200 OK"
16:09:12  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22KGS%22%5D%5D "HTTP/1.1 200 OK"
16:09:12  INFO      shared.erp_adapters.erpnext  │  Record Currency 'KGS' already exists — skipping creation
16:09:12  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22KWD%22%5D%5D "HTTP/1.1 200 OK"
16:09:13  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22KWD%22%5D%5D "HTTP/1.1 200 OK"
16:09:13  INFO      shared.erp_adapters.erpnext  │  Record Currency 'KWD' already exists — skipping creation
16:09:13  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22KRW%22%5D%5D "HTTP/1.1 200 OK"
16:09:13  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22KRW%22%5D%5D "HTTP/1.1 200 OK"
16:09:13  INFO      shared.erp_adapters.erpnext  │  Record Currency 'KRW' already exists — skipping creation
16:09:13  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22KPW%22%5D%5D "HTTP/1.1 200 OK"
16:09:13  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22KPW%22%5D%5D "HTTP/1.1 200 OK"
16:09:13  INFO      shared.erp_adapters.erpnext  │  Record Currency 'KPW' already exists — skipping creation
16:09:13  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22KES%22%5D%5D "HTTP/1.1 200 OK"
16:09:14  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22KES%22%5D%5D "HTTP/1.1 200 OK"
16:09:14  INFO      shared.erp_adapters.erpnext  │  Record Currency 'KES' already exists — skipping creation
16:09:14  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22KZT%22%5D%5D "HTTP/1.1 200 OK"
16:09:14  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22KZT%22%5D%5D "HTTP/1.1 200 OK"
16:09:14  INFO      shared.erp_adapters.erpnext  │  Record Currency 'KZT' already exists — skipping creation
16:09:14  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22JOD%22%5D%5D "HTTP/1.1 200 OK"
16:09:14  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22JOD%22%5D%5D "HTTP/1.1 200 OK"
16:09:14  INFO      shared.erp_adapters.erpnext  │  Record Currency 'JOD' already exists — skipping creation
16:09:14  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22JMD%22%5D%5D "HTTP/1.1 200 OK"
16:09:15  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22JMD%22%5D%5D "HTTP/1.1 200 OK"
16:09:15  INFO      shared.erp_adapters.erpnext  │  Record Currency 'JMD' already exists — skipping creation
16:09:15  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22ILS%22%5D%5D "HTTP/1.1 200 OK"
16:09:15  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22ILS%22%5D%5D "HTTP/1.1 200 OK"
16:09:15  INFO      shared.erp_adapters.erpnext  │  Record Currency 'ILS' already exists — skipping creation
16:09:15  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22IQD%22%5D%5D "HTTP/1.1 200 OK"
16:09:15  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22IQD%22%5D%5D "HTTP/1.1 200 OK"
16:09:15  INFO      shared.erp_adapters.erpnext  │  Record Currency 'IQD' already exists — skipping creation
16:09:15  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22IRR%22%5D%5D "HTTP/1.1 200 OK"
16:09:16  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22IRR%22%5D%5D "HTTP/1.1 200 OK"
16:09:16  INFO      shared.erp_adapters.erpnext  │  Record Currency 'IRR' already exists — skipping creation
16:09:16  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22IDR%22%5D%5D "HTTP/1.1 200 OK"
16:09:16  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22IDR%22%5D%5D "HTTP/1.1 200 OK"
16:09:16  INFO      shared.erp_adapters.erpnext  │  Record Currency 'IDR' already exists — skipping creation
16:09:16  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22ISK%22%5D%5D "HTTP/1.1 200 OK"
16:09:16  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22ISK%22%5D%5D "HTTP/1.1 200 OK"
16:09:16  INFO      shared.erp_adapters.erpnext  │  Record Currency 'ISK' already exists — skipping creation
16:09:16  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22HUF%22%5D%5D "HTTP/1.1 200 OK"
16:09:17  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22HUF%22%5D%5D "HTTP/1.1 200 OK"
16:09:17  INFO      shared.erp_adapters.erpnext  │  Record Currency 'HUF' already exists — skipping creation
16:09:17  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22HKD%22%5D%5D "HTTP/1.1 200 OK"
16:09:17  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22HKD%22%5D%5D "HTTP/1.1 200 OK"
16:09:17  INFO      shared.erp_adapters.erpnext  │  Record Currency 'HKD' already exists — skipping creation
16:09:17  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22HNL%22%5D%5D "HTTP/1.1 200 OK"
16:09:17  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22HNL%22%5D%5D "HTTP/1.1 200 OK"
16:09:17  INFO      shared.erp_adapters.erpnext  │  Record Currency 'HNL' already exists — skipping creation
16:09:17  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22HTG%22%5D%5D "HTTP/1.1 200 OK"
16:09:18  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22HTG%22%5D%5D "HTTP/1.1 200 OK"
16:09:18  INFO      shared.erp_adapters.erpnext  │  Record Currency 'HTG' already exists — skipping creation
16:09:18  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22GYD%22%5D%5D "HTTP/1.1 200 OK"
16:09:18  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22GYD%22%5D%5D "HTTP/1.1 200 OK"
16:09:18  INFO      shared.erp_adapters.erpnext  │  Record Currency 'GYD' already exists — skipping creation
16:09:18  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22GNF%22%5D%5D "HTTP/1.1 200 OK"
16:09:18  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22GNF%22%5D%5D "HTTP/1.1 200 OK"
16:09:18  INFO      shared.erp_adapters.erpnext  │  Record Currency 'GNF' already exists — skipping creation
16:09:19  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22GTQ%22%5D%5D "HTTP/1.1 200 OK"
16:09:19  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22GTQ%22%5D%5D "HTTP/1.1 200 OK"
16:09:19  INFO      shared.erp_adapters.erpnext  │  Record Currency 'GTQ' already exists — skipping creation
16:09:19  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22GIP%22%5D%5D "HTTP/1.1 200 OK"
16:09:19  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22GIP%22%5D%5D "HTTP/1.1 200 OK"
16:09:19  INFO      shared.erp_adapters.erpnext  │  Record Currency 'GIP' already exists — skipping creation
16:09:19  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22GHS%22%5D%5D "HTTP/1.1 200 OK"
16:09:19  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22GHS%22%5D%5D "HTTP/1.1 200 OK"
16:09:19  INFO      shared.erp_adapters.erpnext  │  Record Currency 'GHS' already exists — skipping creation
16:09:20  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22GMD%22%5D%5D "HTTP/1.1 200 OK"
16:09:20  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22GMD%22%5D%5D "HTTP/1.1 200 OK"
16:09:20  INFO      shared.erp_adapters.erpnext  │  Record Currency 'GMD' already exists — skipping creation
16:09:20  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22FJD%22%5D%5D "HTTP/1.1 200 OK"
16:09:20  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22FJD%22%5D%5D "HTTP/1.1 200 OK"
16:09:20  INFO      shared.erp_adapters.erpnext  │  Record Currency 'FJD' already exists — skipping creation
16:09:20  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22FKP%22%5D%5D "HTTP/1.1 200 OK"
16:09:20  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22FKP%22%5D%5D "HTTP/1.1 200 OK"
16:09:20  INFO      shared.erp_adapters.erpnext  │  Record Currency 'FKP' already exists — skipping creation
16:09:21  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22ETB%22%5D%5D "HTTP/1.1 200 OK"
16:09:21  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22ETB%22%5D%5D "HTTP/1.1 200 OK"
16:09:21  INFO      shared.erp_adapters.erpnext  │  Record Currency 'ETB' already exists — skipping creation
16:09:21  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22ERN%22%5D%5D "HTTP/1.1 200 OK"
16:09:21  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22ERN%22%5D%5D "HTTP/1.1 200 OK"
16:09:21  INFO      shared.erp_adapters.erpnext  │  Record Currency 'ERN' already exists — skipping creation
16:09:21  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22EGP%22%5D%5D "HTTP/1.1 200 OK"
16:09:21  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22EGP%22%5D%5D "HTTP/1.1 200 OK"
16:09:21  INFO      shared.erp_adapters.erpnext  │  Record Currency 'EGP' already exists — skipping creation
16:09:21  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22DOP%22%5D%5D "HTTP/1.1 200 OK"
16:09:22  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22DOP%22%5D%5D "HTTP/1.1 200 OK"
16:09:22  INFO      shared.erp_adapters.erpnext  │  Record Currency 'DOP' already exists — skipping creation
16:09:22  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22DJF%22%5D%5D "HTTP/1.1 200 OK"
16:09:22  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22DJF%22%5D%5D "HTTP/1.1 200 OK"
16:09:22  INFO      shared.erp_adapters.erpnext  │  Record Currency 'DJF' already exists — skipping creation
16:09:22  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22DKK%22%5D%5D "HTTP/1.1 200 OK"
16:09:22  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22DKK%22%5D%5D "HTTP/1.1 200 OK"
16:09:22  INFO      shared.erp_adapters.erpnext  │  Record Currency 'DKK' already exists — skipping creation
16:09:22  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22CZK%22%5D%5D "HTTP/1.1 200 OK"
16:09:23  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22CZK%22%5D%5D "HTTP/1.1 200 OK"
16:09:23  INFO      shared.erp_adapters.erpnext  │  Record Currency 'CZK' already exists — skipping creation
16:09:23  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22CYP%22%5D%5D "HTTP/1.1 200 OK"
16:09:23  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22CYP%22%5D%5D "HTTP/1.1 200 OK"
16:09:23  INFO      shared.erp_adapters.erpnext  │  Record Currency 'CYP' already exists — skipping creation
16:09:23  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22CUP%22%5D%5D "HTTP/1.1 200 OK"
16:09:23  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22CUP%22%5D%5D "HTTP/1.1 200 OK"
16:09:23  INFO      shared.erp_adapters.erpnext  │  Record Currency 'CUP' already exists — skipping creation
16:09:23  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22HRK%22%5D%5D "HTTP/1.1 200 OK"
16:09:24  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22HRK%22%5D%5D "HTTP/1.1 200 OK"
16:09:24  INFO      shared.erp_adapters.erpnext  │  Record Currency 'HRK' already exists — skipping creation
16:09:24  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22CRC%22%5D%5D "HTTP/1.1 200 OK"
16:09:24  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22CRC%22%5D%5D "HTTP/1.1 200 OK"
16:09:24  INFO      shared.erp_adapters.erpnext  │  Record Currency 'CRC' already exists — skipping creation
16:09:24  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22CDF%22%5D%5D "HTTP/1.1 200 OK"
16:09:24  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22CDF%22%5D%5D "HTTP/1.1 200 OK"
16:09:24  INFO      shared.erp_adapters.erpnext  │  Record Currency 'CDF' already exists — skipping creation
16:09:24  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22KMF%22%5D%5D "HTTP/1.1 200 OK"
16:09:25  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22KMF%22%5D%5D "HTTP/1.1 200 OK"
16:09:25  INFO      shared.erp_adapters.erpnext  │  Record Currency 'KMF' already exists — skipping creation
16:09:25  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22COP%22%5D%5D "HTTP/1.1 200 OK"
16:09:25  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22COP%22%5D%5D "HTTP/1.1 200 OK"
16:09:25  INFO      shared.erp_adapters.erpnext  │  Record Currency 'COP' already exists — skipping creation
16:09:25  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22CLP%22%5D%5D "HTTP/1.1 200 OK"
16:09:25  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22CLP%22%5D%5D "HTTP/1.1 200 OK"
16:09:25  INFO      shared.erp_adapters.erpnext  │  Record Currency 'CLP' already exists — skipping creation
16:09:25  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22KYD%22%5D%5D "HTTP/1.1 200 OK"
16:09:25  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22KYD%22%5D%5D "HTTP/1.1 200 OK"
16:09:25  INFO      shared.erp_adapters.erpnext  │  Record Currency 'KYD' already exists — skipping creation
16:09:26  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22CVE%22%5D%5D "HTTP/1.1 200 OK"
16:09:26  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22CVE%22%5D%5D "HTTP/1.1 200 OK"
16:09:26  INFO      shared.erp_adapters.erpnext  │  Record Currency 'CVE' already exists — skipping creation
16:09:26  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22CAD%22%5D%5D "HTTP/1.1 200 OK"
16:09:26  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22CAD%22%5D%5D "HTTP/1.1 200 OK"
16:09:26  INFO      shared.erp_adapters.erpnext  │  Record Currency 'CAD' already exists — skipping creation
16:09:26  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22XAF%22%5D%5D "HTTP/1.1 200 OK"
16:09:26  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22XAF%22%5D%5D "HTTP/1.1 200 OK"
16:09:26  INFO      shared.erp_adapters.erpnext  │  Record Currency 'XAF' already exists — skipping creation
16:09:27  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22KHR%22%5D%5D "HTTP/1.1 200 OK"
16:09:27  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22KHR%22%5D%5D "HTTP/1.1 200 OK"
16:09:27  INFO      shared.erp_adapters.erpnext  │  Record Currency 'KHR' already exists — skipping creation
16:09:27  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22BIF%22%5D%5D "HTTP/1.1 200 OK"
16:09:27  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22BIF%22%5D%5D "HTTP/1.1 200 OK"
16:09:27  INFO      shared.erp_adapters.erpnext  │  Record Currency 'BIF' already exists — skipping creation
16:09:27  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22BGN%22%5D%5D "HTTP/1.1 200 OK"
16:09:27  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22BGN%22%5D%5D "HTTP/1.1 200 OK"
16:09:27  INFO      shared.erp_adapters.erpnext  │  Record Currency 'BGN' already exists — skipping creation
16:09:27  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22BND%22%5D%5D "HTTP/1.1 200 OK"
16:09:28  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22BND%22%5D%5D "HTTP/1.1 200 OK"
16:09:28  INFO      shared.erp_adapters.erpnext  │  Record Currency 'BND' already exists — skipping creation
16:09:28  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22BRL%22%5D%5D "HTTP/1.1 200 OK"
16:09:28  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22BRL%22%5D%5D "HTTP/1.1 200 OK"
16:09:28  INFO      shared.erp_adapters.erpnext  │  Record Currency 'BRL' already exists — skipping creation
16:09:28  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22BWP%22%5D%5D "HTTP/1.1 200 OK"
16:09:28  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22BWP%22%5D%5D "HTTP/1.1 200 OK"
16:09:28  INFO      shared.erp_adapters.erpnext  │  Record Currency 'BWP' already exists — skipping creation
16:09:28  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22BAM%22%5D%5D "HTTP/1.1 200 OK"
16:09:29  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22BAM%22%5D%5D "HTTP/1.1 200 OK"
16:09:29  INFO      shared.erp_adapters.erpnext  │  Record Currency 'BAM' already exists — skipping creation
16:09:29  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22BOB%22%5D%5D "HTTP/1.1 200 OK"
16:09:29  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22BOB%22%5D%5D "HTTP/1.1 200 OK"
16:09:29  INFO      shared.erp_adapters.erpnext  │  Record Currency 'BOB' already exists — skipping creation
16:09:29  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22BTN%22%5D%5D "HTTP/1.1 200 OK"
16:09:29  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22BTN%22%5D%5D "HTTP/1.1 200 OK"
16:09:29  INFO      shared.erp_adapters.erpnext  │  Record Currency 'BTN' already exists — skipping creation
16:09:29  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22BMD%22%5D%5D "HTTP/1.1 200 OK"
16:09:29  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22BMD%22%5D%5D "HTTP/1.1 200 OK"
16:09:29  INFO      shared.erp_adapters.erpnext  │  Record Currency 'BMD' already exists — skipping creation
16:09:30  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22XOF%22%5D%5D "HTTP/1.1 200 OK"
16:09:30  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22XOF%22%5D%5D "HTTP/1.1 200 OK"
16:09:30  INFO      shared.erp_adapters.erpnext  │  Record Currency 'XOF' already exists — skipping creation
16:09:30  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22BZD%22%5D%5D "HTTP/1.1 200 OK"
16:09:30  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22BZD%22%5D%5D "HTTP/1.1 200 OK"
16:09:30  INFO      shared.erp_adapters.erpnext  │  Record Currency 'BZD' already exists — skipping creation
16:09:30  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22BBD%22%5D%5D "HTTP/1.1 200 OK"
16:09:30  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22BBD%22%5D%5D "HTTP/1.1 200 OK"
16:09:30  INFO      shared.erp_adapters.erpnext  │  Record Currency 'BBD' already exists — skipping creation
16:09:31  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22BDT%22%5D%5D "HTTP/1.1 200 OK"
16:09:31  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22BDT%22%5D%5D "HTTP/1.1 200 OK"
16:09:31  INFO      shared.erp_adapters.erpnext  │  Record Currency 'BDT' already exists — skipping creation
16:09:31  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22BHD%22%5D%5D "HTTP/1.1 200 OK"
16:09:31  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22BHD%22%5D%5D "HTTP/1.1 200 OK"
16:09:31  INFO      shared.erp_adapters.erpnext  │  Record Currency 'BHD' already exists — skipping creation
16:09:31  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22BSD%22%5D%5D "HTTP/1.1 200 OK"
16:09:31  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22BSD%22%5D%5D "HTTP/1.1 200 OK"
16:09:31  INFO      shared.erp_adapters.erpnext  │  Record Currency 'BSD' already exists — skipping creation
16:09:32  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22AWG%22%5D%5D "HTTP/1.1 200 OK"
16:09:32  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22AWG%22%5D%5D "HTTP/1.1 200 OK"
16:09:32  INFO      shared.erp_adapters.erpnext  │  Record Currency 'AWG' already exists — skipping creation
16:09:32  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22AMD%22%5D%5D "HTTP/1.1 200 OK"
16:09:32  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22AMD%22%5D%5D "HTTP/1.1 200 OK"
16:09:32  INFO      shared.erp_adapters.erpnext  │  Record Currency 'AMD' already exists — skipping creation
16:09:32  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22ARS%22%5D%5D "HTTP/1.1 200 OK"
16:09:32  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22ARS%22%5D%5D "HTTP/1.1 200 OK"
16:09:32  INFO      shared.erp_adapters.erpnext  │  Record Currency 'ARS' already exists — skipping creation
16:09:32  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22XCD%22%5D%5D "HTTP/1.1 200 OK"
16:09:33  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22XCD%22%5D%5D "HTTP/1.1 200 OK"
16:09:33  INFO      shared.erp_adapters.erpnext  │  Record Currency 'XCD' already exists — skipping creation
16:09:33  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22KZ%22%5D%5D "HTTP/1.1 200 OK"
16:09:33  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22KZ%22%5D%5D "HTTP/1.1 200 OK"
16:09:33  INFO      shared.erp_adapters.erpnext  │  Record Currency 'KZ' already exists — skipping creation
16:09:33  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22DZD%22%5D%5D "HTTP/1.1 200 OK"
16:09:33  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22DZD%22%5D%5D "HTTP/1.1 200 OK"
16:09:33  INFO      shared.erp_adapters.erpnext  │  Record Currency 'DZD' already exists — skipping creation
16:09:33  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22ALL%22%5D%5D "HTTP/1.1 200 OK"
16:09:34  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22ALL%22%5D%5D "HTTP/1.1 200 OK"
16:09:34  INFO      shared.erp_adapters.erpnext  │  Record Currency 'ALL' already exists — skipping creation
16:09:34  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22AFN%22%5D%5D "HTTP/1.1 200 OK"
16:09:34  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Currency?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22AFN%22%5D%5D "HTTP/1.1 200 OK"
16:09:34  INFO      shared.erp_adapters.erpnext  │  Record Currency 'AFN' already exists — skipping creation
16:09:34  INFO      is_harness.activity  │    🌱  Currency                seeded=149  already_existed=0  failed=0
16:09:34  INFO      shared.erp_adapters.erpnext  │  ERPNextAdapter.get_doctype_schema: fetching live schema for Payment Terms Template
16:09:34  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/DocType/Payment%20Terms%20Template "HTTP/1.1 200 OK"
16:09:34  INFO      shared.erp_adapters.erpnext  │  ERPNextAdapter.get_doctype_schema: Payment Terms Template → 3 fields
16:09:34  INFO      shared.erp_adapters.erpnext  │  ERPNextAdapter.get_doctype_schema: fetching live schema for Payment Terms Template Detail
16:09:34  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/DocType/Payment%20Terms%20Template%20Detail "HTTP/1.1 200 OK"
16:09:34  INFO      shared.erp_adapters.erpnext  │  ERPNextAdapter.get_doctype_schema: Payment Terms Template Detail → 11 fields
16:09:34  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22Net+7%22%5D%5D "HTTP/1.1 200 OK"
16:09:35  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22Net+7%22%5D%5D "HTTP/1.1 200 OK"
16:09:35  INFO      shared.erp_adapters.erpnext  │  Record Payment Terms Template 'Net 7' already exists — skipping creation
16:09:35  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22Net+15%22%5D%5D "HTTP/1.1 200 OK"
16:09:35  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22Net+15%22%5D%5D "HTTP/1.1 200 OK"
16:09:35  INFO      shared.erp_adapters.erpnext  │  Record Payment Terms Template 'Net 15' already exists — skipping creation
16:09:35  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22Net+30%22%5D%5D "HTTP/1.1 200 OK"
16:09:35  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22Net+30%22%5D%5D "HTTP/1.1 200 OK"
16:09:35  INFO      shared.erp_adapters.erpnext  │  Record Payment Terms Template 'Net 30' already exists — skipping creation
16:09:35  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22Net+45%22%5D%5D "HTTP/1.1 200 OK"
16:09:36  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22Net+45%22%5D%5D "HTTP/1.1 200 OK"
16:09:36  INFO      shared.erp_adapters.erpnext  │  Record Payment Terms Template 'Net 45' already exists — skipping creation
16:09:36  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22Net+60%22%5D%5D "HTTP/1.1 200 OK"
16:09:36  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22Net+60%22%5D%5D "HTTP/1.1 200 OK"
16:09:36  INFO      shared.erp_adapters.erpnext  │  Record Payment Terms Template 'Net 60' already exists — skipping creation
16:09:36  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22Net+90%22%5D%5D "HTTP/1.1 200 OK"
16:09:36  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22Net+90%22%5D%5D "HTTP/1.1 200 OK"
16:09:36  INFO      shared.erp_adapters.erpnext  │  Record Payment Terms Template 'Net 90' already exists — skipping creation
16:09:36  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22Immediate%22%5D%5D "HTTP/1.1 200 OK"
16:09:37  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22Immediate%22%5D%5D "HTTP/1.1 200 OK"
16:09:37  INFO      shared.erp_adapters.erpnext  │  Record Payment Terms Template 'Immediate' already exists — skipping creation
16:09:37  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22COD%22%5D%5D "HTTP/1.1 200 OK"
16:09:37  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22COD%22%5D%5D "HTTP/1.1 200 OK"
16:09:37  INFO      shared.erp_adapters.erpnext  │  Record Payment Terms Template 'COD' already exists — skipping creation
16:09:37  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22Advance%22%5D%5D "HTTP/1.1 200 OK"
16:09:37  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22Advance%22%5D%5D "HTTP/1.1 200 OK"
16:09:37  INFO      shared.erp_adapters.erpnext  │  Record Payment Terms Template 'Advance' already exists — skipping creation
16:09:37  INFO      is_harness.activity  │    🌱  [SUPP] Payment Terms Template  seeded=9  already_existed=0  failed=0
16:09:37  INFO      is_harness.activity  │
16:09:37  INFO      is_harness.activity  │    🔍  PASS 2 — scanning 33 step(s) for unknown link targets
16:09:37  INFO      is_harness.activity  │    🔍    skip step doctype=Sales Order action=data_gap (not create)
16:09:37  INFO      is_harness.activity  │    🔍    skip step doctype=Delivery Note action=data_gap (not create)
16:09:37  INFO      is_harness.activity  │    🔍    skip step doctype=Work Order action=data_gap (not create)
16:09:37  INFO      is_harness.activity  │    🔍    skip step doctype=Sales Invoice action=data_gap (not create)
16:09:37  INFO      is_harness.activity  │    🔍    skip step doctype=BOM (Formulation) action=data_gap (not create)
16:09:37  INFO      is_harness.activity  │    🔍    skip step doctype=Batch action=data_gap (not create)
16:09:37  INFO      is_harness.activity  │    🔍    skip step doctype=Branch action=data_gap (not create)
16:09:37  INFO      is_harness.activity  │    🔍    skip step doctype=Customer or Lead action=data_gap (not create)
16:09:37  INFO      is_harness.activity  │    🔍    skip step doctype=Department action=data_gap (not create)
16:09:37  INFO      is_harness.activity  │    🔍    skip step doctype=Designation action=data_gap (not create)
16:09:37  INFO      is_harness.activity  │    🔍    skip step doctype=DocType action=data_gap (not create)
16:09:37  INFO      is_harness.activity  │    🔍    skip step doctype=Employee action=data_gap (not create)
16:09:37  INFO      is_harness.activity  │    🔍    skip step doctype=Gender action=data_gap (not create)
16:09:37  INFO      is_harness.activity  │    🔍    skip step doctype=Holiday List action=data_gap (not create)
16:09:37  INFO      is_harness.activity  │    🔍    skip step doctype=Issue action=data_gap (not create)
16:09:37  INFO      is_harness.activity  │    🔍    skip step doctype=Item Attribute action=data_gap (not create)
16:09:37  INFO      is_harness.activity  │    🔍    skip step doctype=Item Variant action=data_gap (not create)
16:09:37  INFO      is_harness.activity  │    🔍    skip step doctype=Job Card action=data_gap (not create)
16:09:37  INFO      is_harness.activity  │    🔍    skip step doctype=Letter Head action=data_gap (not create)
16:09:37  INFO      is_harness.activity  │    🔍    skip step doctype=Operation action=data_gap (not create)
16:09:37  INFO      is_harness.activity  │    🔍    skip step doctype=Plant Floor action=data_gap (not create)
16:09:37  INFO      is_harness.activity  │    🔍    skip step doctype=Project Type action=data_gap (not create)
16:09:37  INFO      is_harness.activity  │    🔍    skip step doctype=Quality Inspection action=data_gap (not create)
16:09:37  INFO      is_harness.activity  │    🔍    skip step doctype=Quality Inspection Template action=data_gap (not create)
16:09:37  INFO      is_harness.activity  │    🔍    skip step doctype=Quotation action=data_gap (not create)
16:09:37  INFO      is_harness.activity  │    🔍    skip step doctype=Salutation action=data_gap (not create)
16:09:37  INFO      is_harness.activity  │    🔍    skip step doctype=Serial No action=data_gap (not create)
16:09:37  INFO      is_harness.activity  │    🔍    skip step doctype=Stock Entry (Issue, Transfer, Manufacture) action=data_gap (not create)
16:09:37  INFO      is_harness.activity  │    🔍    skip step doctype=Task Type action=data_gap (not create)
16:09:37  INFO      is_harness.activity  │    🔍    skip step doctype=User action=data_gap (not create)
16:09:37  INFO      is_harness.activity  │    🔍    skip step doctype=Work Order (Batch Ticket) action=data_gap (not create)
16:09:37  INFO      is_harness.activity  │    🔍    skip step doctype=Workstation action=data_gap (not create)
16:09:37  INFO      is_harness.activity  │    🔍    skip step doctype=Workstation Type action=data_gap (not create)
16:09:37  INFO      is_harness.activity  │    🔍  PASS 2 — No unknown link targets found, skipping
16:09:37  INFO      is_harness.activity  │
16:09:37  INFO      is_harness.activity  │    🔗  PASS 2.5 — Bulk link pre-resolution
16:09:37  INFO      is_harness.activity  │    Pass 2.5 — No link targets to resolve
16:09:37  INFO      is_harness.activity  │
16:09:37  WARNING   is_harness.activity  │    ⚠️  DATA GAP: Sales Order has no mapped data file and no baseline — skipping
16:09:37  WARNING   is_harness.activity  │    ⚠️  DATA GAP: Delivery Note has no mapped data file and no baseline — skipping
16:09:37  WARNING   is_harness.activity  │    ⚠️  DATA GAP: Work Order has no mapped data file and no baseline — skipping
16:09:37  WARNING   is_harness.activity  │    ⚠️  DATA GAP: Sales Invoice has no mapped data file and no baseline — skipping
16:09:37  WARNING   is_harness.activity  │    ⚠️  DATA GAP: BOM (Formulation) has no mapped data file and no baseline — skipping
16:09:37  WARNING   is_harness.activity  │    ⚠️  DATA GAP: Batch has no mapped data file and no baseline — skipping
16:09:37  WARNING   is_harness.activity  │    ⚠️  DATA GAP: Branch has no mapped data file and no baseline — skipping
16:09:37  WARNING   is_harness.activity  │    ⚠️  DATA GAP: Customer or Lead has no mapped data file and no baseline — skipping
16:09:37  WARNING   is_harness.activity  │    ⚠️  DATA GAP: Department has no mapped data file and no baseline — skipping
16:09:37  WARNING   is_harness.activity  │    ⚠️  DATA GAP: Designation has no mapped data file and no baseline — skipping
16:09:37  WARNING   is_harness.activity  │    ⚠️  DATA GAP: DocType has no mapped data file and no baseline — skipping
16:09:37  WARNING   is_harness.activity  │    ⚠️  DATA GAP: Employee has no mapped data file and no baseline — skipping
16:09:37  WARNING   is_harness.activity  │    ⚠️  DATA GAP: Gender has no mapped data file and no baseline — skipping
16:09:37  WARNING   is_harness.activity  │    ⚠️  DATA GAP: Holiday List has no mapped data file and no baseline — skipping
16:09:37  WARNING   is_harness.activity  │    ⚠️  DATA GAP: Issue has no mapped data file and no baseline — skipping
16:09:37  WARNING   is_harness.activity  │    ⚠️  DATA GAP: Item Attribute has no mapped data file and no baseline — skipping
16:09:37  WARNING   is_harness.activity  │    ⚠️  DATA GAP: Item Variant has no mapped data file and no baseline — skipping
16:09:37  WARNING   is_harness.activity  │    ⚠️  DATA GAP: Job Card has no mapped data file and no baseline — skipping
16:09:37  WARNING   is_harness.activity  │    ⚠️  DATA GAP: Letter Head has no mapped data file and no baseline — skipping
16:09:37  WARNING   is_harness.activity  │    ⚠️  DATA GAP: Operation has no mapped data file and no baseline — skipping
16:09:37  WARNING   is_harness.activity  │    ⚠️  DATA GAP: Plant Floor has no mapped data file and no baseline — skipping
16:09:37  WARNING   is_harness.activity  │    ⚠️  DATA GAP: Project Type has no mapped data file and no baseline — skipping
16:09:37  WARNING   is_harness.activity  │    ⚠️  DATA GAP: Quality Inspection has no mapped data file and no baseline — skipping
16:09:37  WARNING   is_harness.activity  │    ⚠️  DATA GAP: Quality Inspection Template has no mapped data file and no baseline — skipping
16:09:37  WARNING   is_harness.activity  │    ⚠️  DATA GAP: Quotation has no mapped data file and no baseline — skipping
16:09:37  WARNING   is_harness.activity  │    ⚠️  DATA GAP: Salutation has no mapped data file and no baseline — skipping
16:09:37  WARNING   is_harness.activity  │    ⚠️  DATA GAP: Serial No has no mapped data file and no baseline — skipping
16:09:37  WARNING   is_harness.activity  │    ⚠️  DATA GAP: Stock Entry (Issue, Transfer, Manufacture) has no mapped data file and no baseline — skipping
16:09:37  WARNING   is_harness.activity  │    ⚠️  DATA GAP: Task Type has no mapped data file and no baseline — skipping
16:09:37  WARNING   is_harness.activity  │    ⚠️  DATA GAP: User has no mapped data file and no baseline — skipping
16:09:37  WARNING   is_harness.activity  │    ⚠️  DATA GAP: Work Order (Batch Ticket) has no mapped data file and no baseline — skipping
16:09:37  WARNING   is_harness.activity  │    ⚠️  DATA GAP: Workstation has no mapped data file and no baseline — skipping
16:09:37  WARNING   is_harness.activity  │    ⚠️  DATA GAP: Workstation Type has no mapped data file and no baseline — skipping
16:09:39  INFO      is_harness.activity  │  ✅ execute_import_phase done | phase=phase_c_transactional records=0
16:09:39  INFO      is_harness  │
16:09:39  INFO      is_harness  │  ════════════════════════════════════════════════════════════════════════
16:09:39  INFO      is_harness  │    ✅  STEP COMPLETE: execute_import_phase
16:09:39  INFO      is_harness  │  ════════════════════════════════════════════════════════════════════════
16:09:39  INFO      is_harness  │

{
  "phase": "phase_c_transactional",
  "status": "success",
  "steps_completed": 0,
  "steps_failed": 0,
  "records_created": 0,
  "execution_logs": []
}




### and supabase query result :
[
	{
		"step": 17,
		"action": "data_gap",
		"doctype": "Sales Order",
		"records": 0,
		"data_source": "none"
	},
	{
		"step": 18,
		"action": "data_gap",
		"doctype": "Delivery Note",
		"records": 0,
		"data_source": "none"
	},
	{
		"step": 19,
		"action": "data_gap",
		"doctype": "Work Order",
		"records": 0,
		"data_source": "none"
	},
	{
		"step": 20,
		"action": "data_gap",
		"doctype": "Sales Invoice",
		"records": 0,
		"data_source": "none"
	},
	{
		"step": 25,
		"action": "data_gap",
		"doctype": "BOM (Formulation)",
		"records": 0,
		"data_source": "none"
	},
	{
		"step": 26,
		"action": "data_gap",
		"doctype": "Batch",
		"records": 0,
		"data_source": "none"
	},
	{
		"step": 27,
		"action": "data_gap",
		"doctype": "Branch",
		"records": 0,
		"data_source": "none"
	},
	{
		"step": 28,
		"action": "data_gap",
		"doctype": "Customer or Lead",
		"records": 0,
		"data_source": "none"
	},
	{
		"step": 29,
		"action": "data_gap",
		"doctype": "Department",
		"records": 0,
		"data_source": "none"
	},
	{
		"step": 30,
		"action": "data_gap",
		"doctype": "Designation",
		"records": 0,
		"data_source": "none"
	},
	{
		"step": 31,
		"action": "data_gap",
		"doctype": "DocType",
		"records": 0,
		"data_source": "none"
	},
	{
		"step": 32,
		"action": "data_gap",
		"doctype": "Employee",
		"records": 0,
		"data_source": "none"
	},
	{
		"step": 33,
		"action": "data_gap",
		"doctype": "Gender",
		"records": 0,
		"data_source": "none"
	},
	{
		"step": 34,
		"action": "data_gap",
		"doctype": "Holiday List",
		"records": 0,
		"data_source": "none"
	},
	{
		"step": 35,
		"action": "data_gap",
		"doctype": "Issue",
		"records": 0,
		"data_source": "none"
	},
	{
		"step": 36,
		"action": "data_gap",
		"doctype": "Item Attribute",
		"records": 0,
		"data_source": "none"
	},
	{
		"step": 37,
		"action": "data_gap",
		"doctype": "Item Variant",
		"records": 0,
		"data_source": "none"
	},
	{
		"step": 38,
		"action": "data_gap",
		"doctype": "Job Card",
		"records": 0,
		"data_source": "none"
	},
	{
		"step": 39,
		"action": "data_gap",
		"doctype": "Letter Head",
		"records": 0,
		"data_source": "none"
	},
	{
		"step": 40,
		"action": "data_gap",
		"doctype": "Operation",
		"records": 0,
		"data_source": "none"
	},
	{
		"step": 41,
		"action": "data_gap",
		"doctype": "Plant Floor",
		"records": 0,
		"data_source": "none"
	},
	{
		"step": 42,
		"action": "data_gap",
		"doctype": "Project Type",
		"records": 0,
		"data_source": "none"
	},
	{
		"step": 43,
		"action": "data_gap",
		"doctype": "Quality Inspection",
		"records": 0,
		"data_source": "none"
	},
	{
		"step": 44,
		"action": "data_gap",
		"doctype": "Quality Inspection Template",
		"records": 0,
		"data_source": "none"
	},
	{
		"step": 45,
		"action": "data_gap",
		"doctype": "Quotation",
		"records": 0,
		"data_source": "none"
	},
	{
		"step": 46,
		"action": "data_gap",
		"doctype": "Salutation",
		"records": 0,
		"data_source": "none"
	},
	{
		"step": 47,
		"action": "data_gap",
		"doctype": "Serial No",
		"records": 0,
		"data_source": "none"
	},
	{
		"step": 48,
		"action": "data_gap",
		"doctype": "Stock Entry (Issue, Transfer, Manufacture)",
		"records": 0,
		"data_source": "none"
	},
	{
		"step": 49,
		"action": "data_gap",
		"doctype": "Task Type",
		"records": 0,
		"data_source": "none"
	},
	{
		"step": 50,
		"action": "data_gap",
		"doctype": "User",
		"records": 0,
		"data_source": "none"
	},
	{
		"step": 51,
		"action": "data_gap",
		"doctype": "Work Order (Batch Ticket)",
		"records": 0,
		"data_source": "none"
	},
	{
		"step": 52,
		"action": "data_gap",
		"doctype": "Workstation",
		"records": 0,
		"data_source": "none"
	},
	{
		"step": 53,
		"action": "data_gap",
		"doctype": "Workstation Type",
		"records": 0,
		"data_source": "none"
	}
]

---

**Cursor**

Good news: **Pass 2.5 is wired correctly** — you can see it ran:

```
🔗  PASS 2.5 — Bulk link pre-resolution
Pass 2.5 — No link targets to resolve
```

Bad news: **there was nothing to resolve or import**. Every Phase C step is still `data_gap`. The link-resolution fix never got exercised because no rows reached the import loop.

## What the logs actually tell us

| Signal | Meaning |
|---|---|
| `dry_run=False` | Live mode — correct |
| `finalize_import_plan → ready` | Plan updated without validation blockers — **not** “all doctypes have mapped files” |
| All steps `action=data_gap` | Import plan has **zero** `create` steps with R2 paths |
| Pass 2.5: “No link targets” | No `create` rows to scan — expected given above |
| `records=0` | Nothing imported |

So this is **not** a link-resolution failure. It’s a **mapping/plan wiring** problem for session `3145be35-2991-48dd-b43e-e59df9e86f5c`.

## Root cause

`finalize_import_plan` only wires mapped files into steps that are already:

- `action: "create"`, or  
- `data_source: "pending_mapping"`

Your Supabase result shows every Phase C step is already `data_gap` with `data_source: "none"`. That usually means one of:

1. **`is_mapped_data` is empty** for this session (mapping never completed / wrong session), or  
2. **Doctype name mismatch** — mapped data exists but under a different name than the plan expects.

Your plan expects names like:
- `Work Order`
- `Work Order (Batch Ticket)`
- `BOM (Formulation)`

If `is_mapped_data.target_doctype` is e.g. `Work Order` but the plan step is `Work Order (Batch Ticket)`, finalize won’t link them.

## Run these Supabase checks next

**1. Do mapped payloads exist at all?**

```sql
SELECT target_doctype, total_rows, mapped_payload_r2_path, validation_status, created_at
FROM is_mapped_data
WHERE session_id = '3145be35-2991-48dd-b43e-e59df9e86f5c'
ORDER BY target_doctype;
```

**2. Was the original failure on a different session?**

```sql
SELECT s.id AS session_id, s.status, s.created_at,
       COUNT(m.id) AS mapped_doctypes
FROM is_sessions s
LEFT JOIN is_mapped_data m ON m.session_id = s.id
WHERE s.project_id = 'b6ff0b7f-a616-4179-8f68-deda9b3578af'
GROUP BY s.id, s.status, s.created_at
ORDER BY s.created_at DESC;
```

**3. Did any import actually run before?**

```sql
SELECT doctype, status, records_attempted, records_succeeded, records_failed, error_message, started_at
FROM is_import_logs
WHERE import_plan_id = '721f27cc-8b37-4471-ac59-f1b08a924d1a'
ORDER BY started_at DESC;
```

If `is_import_logs` has Work Order failures but `is_mapped_data` is empty for this session, the **Temporal workflow run used different state** than what the harness is reading now.

## What to do depending on query results

### Case A — `is_mapped_data` has rows, but names don’t match plan

Example: mapped `Work Order`, plan expects `Work Order (Batch Ticket)`.

You need to either:
- Re-run mapping so `target_doctype` matches the plan step name, or  
- Fix the target structure / plan doctype names to match what mapping produced, then run `finalize_import_plan` again.

Only after a step shows `"action": "create"` and a real R2 path will Pass 2.5 matter.

### Case B — `is_mapped_data` is empty

Mapping never landed for this session. You need to re-run the pipeline from mapping onward:

```powershell
# If you have mapped files ready in R2/DB from uploads:
python -m containers.implementation.is_harness --step map_file_to_erpnext
python -m containers.implementation.is_harness --step validate_mapped_data
python -m containers.implementation.is_harness --step finalize_import_plan
python -m containers.implementation.is_harness --step execute_import_phase --phase phase_c_transactional
```

Or upload Work Order CSV again through the UI and confirm mapping completes.

### Case C — Another session has the mapped Work Order data

Update `execute_import_phase.json` (and `finalize_import_plan.json`) to use **that** `session_id`, then rerun finalize + Phase C.

## Fastest path to test link resolution specifically

If you just want to prove `WIP - Factory → WIP - GS` works, you don’t need the full onboarding replay:

1. Create a **small Work Order CSV** (2 rows, wrong warehouse names, new WO IDs) — use the prompt I gave earlier.
2. Upload + map it for Green Surface.
3. Confirm Supabase shows something like:

```json
{
  "doctype": "Work Order",
  "action": "create",
  "data_source": "green-surface/.../mapped/Work Order.json",
  "records": 2
}
```

4. Re-run Phase C harness.

Then you should see:

```
Pass 2.5 — Bulk resolving 1 doctype(s): Warehouse, ...
BulkLinkResolver: Warehouse 'WIP - Factory' -> 'WIP - GS'
```

## Bottom line

- Link Resolution V2 **did run** — there was simply **no data attached to the plan**.
- `finalize_import_plan → ready` is misleading here; it only means “not blocked by validation,” not “Phase C has importable rows.”
- Your next move is **not** another Phase C rerun — it’s finding/fixing why `is_mapped_data` isn’t linked to plan steps.

Paste the result of query **#1** (`is_mapped_data` for this session) and I can tell you exactly which case you’re in and the minimal next step.

---

**User**

1. Success. No rows returned

2. [
  {
    "session_id": "3145be35-2991-48dd-b43e-e59df9e86f5c",
    "status": "awaiting_files",
    "created_at": "2026-05-24 08:48:23.779139+00",
    "mapped_doctypes": 0
  },
  {
    "session_id": "8a1d1297-39d3-4b88-82a3-cbca4983218b",
    "status": "complete",
    "created_at": "2026-05-24 06:31:50.898605+00",
    "mapped_doctypes": 3
  }
]

3. Success. No rows returned




---

**Cursor**

That explains everything. You’ve been testing against the **wrong session**.

## Diagnosis

| Session | Status | Mapped doctypes | Verdict |
|---|---|---|---|
| `3145be35-...` | `awaiting_files` | **0** | Harness fixture session — **no files mapped, nothing to import** |
| `8a1d1297-...` | `complete` | **3** | Real session — **this is where your Work Order data lives** |

The Green Surface fixture in `dev_fixtures/` points at `3145be35`, which never got past file upload. That’s why:

- `is_mapped_data` is empty
- Every Phase C step is `data_gap`
- Pass 2.5 finds nothing to resolve
- `is_import_logs` is empty

Your original `417 LinkValidationError` on Work Order almost certainly came from session **`8a1d1297-39d3-4b88-82a3-cbca4983218b`**, not the harness fixture session.

---

## What to do now

### Step 1 — Inspect the real session’s mapped data

```sql
SELECT target_doctype, total_rows, mapped_payload_r2_path, validation_status
FROM is_mapped_data
WHERE session_id = '8a1d1297-39d3-4b88-82a3-cbca4983218b'
ORDER BY target_doctype;
```

Confirm one of the 3 rows is **Work Order** (or similar).

Also check its import plan:

```sql
SELECT id, status, phases->'phase_c_transactional'->'steps' AS phase_c_steps
FROM is_import_plans
WHERE session_id = '8a1d1297-39d3-4b88-82a3-cbca4983218b'
ORDER BY created_at DESC
LIMIT 1;
```

You want at least one step with `"action": "create"` and a real R2 path — not `"data_source": "none"`.

### Step 2 — Point the harness at the correct session

Update both fixtures to use session `8a1d1297-39d3-4b88-82a3-cbca4983218b`:

- `containers/implementation/dev_fixtures/execute_import_phase.json`
- `containers/implementation/dev_fixtures/finalize_import_plan.json`

Change `"session_id"` from `3145be35-...` to `8a1d1297-39d3-4b88-82a3-cbca4983218b`.  
(`project_id` and `company_slug` stay the same — same Green Surface project.)

### Step 3 — Re-run on the correct session

```powershell
python -m containers.implementation.is_harness --step finalize_import_plan
python -m containers.implementation.is_harness --step execute_import_phase --phase phase_c_transactional
```

Make sure `"dry_run": false` in the execute fixture.

### Step 4 — What success looks like

```
🔗  PASS 2.5 — Bulk link pre-resolution
Pass 2.5 — Bulk resolving N doctype(s): Warehouse, ...
BulkLinkResolver: Warehouse 'WIP - Factory' -> 'WIP - GS'
```

And in the JSON output, `execution_logs` should have a Work Order entry with `resolution_summary` and `records_succeeded > 0`.

---

## Optional: check if the original failure was logged

```sql
SELECT il.doctype, il.status, il.records_failed, il.error_message, il.started_at
FROM is_import_logs il
JOIN is_import_plans ip ON ip.id = il.import_plan_id
WHERE ip.session_id = '8a1d1297-39d3-4b88-82a3-cbca4983218b'
ORDER BY il.started_at DESC;
```

That should show the earlier Work Order 417 errors if Phase C ran via Temporal on that session.

---

## Summary

You don’t need new dummy CSVs yet. The data is already mapped on session `8a1d1297`. The harness was pointed at an empty session (`3145be35`, still `awaiting_files`).

Switch the fixture `session_id`, rerun finalize + Phase C, and you should finally hit the link-resolution path with real Work Order rows.

If you paste the result of the `is_mapped_data` query for `8a1d1297`, I can confirm whether Work Order is one of the 3 mapped doctypes before you rerun.

---

**User**

PS C:\dev\F3Next> python -m containers.implementation.is_harness --step finalize_import_plan
16:18:13  INFO      is_harness  │
16:18:13  INFO      is_harness  │  ════════════════════════════════════════════════════════════════════════
16:18:13  INFO      is_harness  │    IS STEP HARNESS
16:18:13  INFO      is_harness  │    step     : finalize_import_plan
16:18:13  INFO      is_harness  │    mock_llm : False
16:18:13  INFO      is_harness  │    dry_run  : False
16:18:13  INFO      is_harness  │  ════════════════════════════════════════════════════════════════════════
16:18:13  INFO      is_harness  │
16:18:14  INFO      is_harness  │    Fixture  : C:\dev\F3Next\containers\implementation\dev_fixtures\finalize_import_plan.json
16:18:14  INFO      is_harness  │    Input    : {"_comment": "Finalizes import plan using actual mapping locations and validation checks.", "session_id": "8a1d1297-39d3-4b88-82a3-cbca4983218b", "project_id": "b6ff0b7f-a616-4179-8f68-deda9b3578af", ...
16:18:14  INFO      is_harness  │
16:18:14  INFO      is_harness.activity  │  ▶ finalize_import_plan started | session=8a1d1297-39d3-4b88-82a3-cbca4983218b
16:18:20  INFO      is_harness.activity  │    ✅ Finalized R2 plan uploaded.
16:18:20  INFO      is_harness.activity  │    ✅ Finalized ISImportPlan database record updated | id=455fa0aa-1e00-4559-9f82-dea6dd36cdb6 status=ready
16:18:20  INFO      is_harness  │
16:18:20  INFO      is_harness  │  ════════════════════════════════════════════════════════════════════════
16:18:20  INFO      is_harness  │    ✅  STEP COMPLETE: finalize_import_plan
16:18:20  INFO      is_harness  │  ════════════════════════════════════════════════════════════════════════
16:18:20  INFO      is_harness  │

"ready"

PS C:\dev\F3Next> python -m containers.implementation.is_harness --step execute_import_phase --phase phase_c_transactional
16:18:22  INFO      is_harness  │
16:18:22  INFO      is_harness  │  ════════════════════════════════════════════════════════════════════════
16:18:22  INFO      is_harness  │    IS STEP HARNESS
16:18:22  INFO      is_harness  │    step     : execute_import_phase
16:18:22  INFO      is_harness  │    mock_llm : False
16:18:22  INFO      is_harness  │    dry_run  : False
16:18:22  INFO      is_harness  │  ════════════════════════════════════════════════════════════════════════
16:18:22  INFO      is_harness  │
16:18:24  INFO      is_harness  │    Fixture  : C:\dev\F3Next\containers\implementation\dev_fixtures\execute_import_phase.json
16:18:24  INFO      is_harness  │    Input    : {"_comment": "Executes one import phase against ERPNext. Use --dry-run to skip actual API writes. Requires build_import_plan to have run first for this session.", "session_id": "8a1d1297-39d3-4b88-82a...
16:18:24  INFO      is_harness  │
16:18:24  INFO      is_harness.activity  │  ▶ execute_import_phase started | session=8a1d1297-39d3-4b88-82a3-cbca4983218b phase=phase_c_transactional dry_run=False
16:18:30  INFO      is_harness.activity  │    🔑 Auto-resolved base_url from Project.deployment_details: https://green-surface.f3next.in
16:18:30  INFO      is_harness.activity  │    🔑 Auto-resolved API credentials from Project.deployment_details
16:18:30  INFO      shared.erp_adapters.erpnext  │  ERPNextAdapter.get_doctype_schema: fetching live schema for Payment Terms Template
16:18:31  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/DocType/Payment%20Terms%20Template "HTTP/1.1 200 OK"
16:18:31  INFO      shared.erp_adapters.erpnext  │  ERPNextAdapter.get_doctype_schema: Payment Terms Template → 3 fields
16:18:31  INFO      shared.erp_adapters.erpnext  │  ERPNextAdapter.get_doctype_schema: fetching live schema for Payment Terms Template Detail
16:18:31  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/DocType/Payment%20Terms%20Template%20Detail "HTTP/1.1 200 OK"
16:18:31  INFO      shared.erp_adapters.erpnext  │  ERPNextAdapter.get_doctype_schema: Payment Terms Template Detail → 11 fields
16:18:31  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22Net+7%22%5D%5D "HTTP/1.1 200 OK"
16:18:31  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22Net+7%22%5D%5D "HTTP/1.1 200 OK"
16:18:31  INFO      shared.erp_adapters.erpnext  │  Record Payment Terms Template 'Net 7' already exists — skipping creation
16:18:31  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22Net+15%22%5D%5D "HTTP/1.1 200 OK"
16:18:32  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22Net+15%22%5D%5D "HTTP/1.1 200 OK"
16:18:32  INFO      shared.erp_adapters.erpnext  │  Record Payment Terms Template 'Net 15' already exists — skipping creation
16:18:32  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22Net+30%22%5D%5D "HTTP/1.1 200 OK"
16:18:32  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22Net+30%22%5D%5D "HTTP/1.1 200 OK"
16:18:32  INFO      shared.erp_adapters.erpnext  │  Record Payment Terms Template 'Net 30' already exists — skipping creation
16:18:32  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22Net+45%22%5D%5D "HTTP/1.1 200 OK"
16:18:32  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22Net+45%22%5D%5D "HTTP/1.1 200 OK"
16:18:32  INFO      shared.erp_adapters.erpnext  │  Record Payment Terms Template 'Net 45' already exists — skipping creation
16:18:32  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22Net+60%22%5D%5D "HTTP/1.1 200 OK"
16:18:33  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22Net+60%22%5D%5D "HTTP/1.1 200 OK"
16:18:33  INFO      shared.erp_adapters.erpnext  │  Record Payment Terms Template 'Net 60' already exists — skipping creation
16:18:33  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22Net+90%22%5D%5D "HTTP/1.1 200 OK"
16:18:33  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22Net+90%22%5D%5D "HTTP/1.1 200 OK"
16:18:33  INFO      shared.erp_adapters.erpnext  │  Record Payment Terms Template 'Net 90' already exists — skipping creation
16:18:33  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22Immediate%22%5D%5D "HTTP/1.1 200 OK"
16:18:33  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22Immediate%22%5D%5D "HTTP/1.1 200 OK"
16:18:33  INFO      shared.erp_adapters.erpnext  │  Record Payment Terms Template 'Immediate' already exists — skipping creation
16:18:33  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22COD%22%5D%5D "HTTP/1.1 200 OK"
16:18:34  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22COD%22%5D%5D "HTTP/1.1 200 OK"
16:18:34  INFO      shared.erp_adapters.erpnext  │  Record Payment Terms Template 'COD' already exists — skipping creation
16:18:34  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22Advance%22%5D%5D "HTTP/1.1 200 OK"
16:18:34  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22Advance%22%5D%5D "HTTP/1.1 200 OK"
16:18:34  INFO      shared.erp_adapters.erpnext  │  Record Payment Terms Template 'Advance' already exists — skipping creation
16:18:34  INFO      is_harness.activity  │    🌱  [SUPP] Payment Terms Template  seeded=9  already_existed=0  failed=0
16:18:34  INFO      is_harness.activity  │
16:18:34  INFO      is_harness.activity  │    🔍  PASS 2 — scanning 3 step(s) for unknown link targets
16:18:34  INFO      is_harness.activity  │    🔍    skip step doctype=Stock Entry action=data_gap (not create)
16:18:34  INFO      is_harness.activity  │    🔍    skip step doctype=Purchase Receipt action=data_gap (not create)
16:18:34  INFO      is_harness.activity  │    🔍    processing step doctype=Work Order
16:18:36  INFO      is_harness.activity  │    🔍  PASS 2 — No unknown link targets found, skipping
16:18:36  INFO      is_harness.activity  │
16:18:36  INFO      is_harness.activity  │    🔗  PASS 2.5 — Bulk link pre-resolution
16:18:36  INFO      is_harness.activity  │    Pass 2.5 — Bulk resolving 3 doctype(s): BOM, Item, Warehouse
16:18:36  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Item?fields=%5B%22name%22%2C+%22disabled%22%5D&limit_page_length=1000&limit_start=0&filters=%5B%5B%22disabled%22%2C+%22%3D%22%2C+0%5D%5D "HTTP/1.1 200 OK"
16:18:37  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/BOM?fields=%5B%22name%22%2C+%22disabled%22%5D&limit_page_length=1000&limit_start=0&filters=%5B%5B%22disabled%22%2C+%22%3D%22%2C+0%5D%5D "HTTP/1.1 417 Expectation Failed"
16:18:37  WARNING   is_harness.activity  │  BulkLinkResolver: disabled-filter fetch failed for BOM: ERPNext error 417: DataError: frappe.exceptions.DataError: Field not permitted in query: disabled
16:18:37  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/BOM?fields=%5B%22name%22%5D&limit_page_length=1000&limit_start=0 "HTTP/1.1 200 OK"
16:18:37  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Warehouse?fields=%5B%22name%22%2C+%22disabled%22%5D&limit_page_length=1000&limit_start=0&filters=%5B%5B%22disabled%22%2C+%22%3D%22%2C+0%5D%5D "HTTP/1.1 200 OK"
16:18:37  WARNING   is_harness.activity  │  BulkLinkResolver: unresolvable Warehouse 'WIP - Factory'
16:18:37  ERROR     is_harness  │
16:18:37  ERROR     is_harness  │    ❌  STEP FAILED: name 'target_doctype' is not defined
16:18:37  ERROR     is_harness  │
Traceback (most recent call last):
  File "<frozen runpy>", line 198, in _run_module_as_main
  File "<frozen runpy>", line 88, in _run_code
  File "C:\dev\F3Next\containers\implementation\is_harness.py", line 516, in <module>
    asyncio.run(_main())
    ~~~~~~~~~~~^^^^^^^^^
  File "C:\Users\Mayur Laxman Aldar\AppData\Local\Programs\Python\Python313\Lib\asyncio\runners.py", line 195, in run
    return runner.run(main)
           ~~~~~~~~~~^^^^^^
  File "C:\Users\Mayur Laxman Aldar\AppData\Local\Programs\Python\Python313\Lib\asyncio\runners.py", line 118, in run
    return self._loop.run_until_complete(task)
           ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
  File "C:\Users\Mayur Laxman Aldar\AppData\Local\Programs\Python\Python313\Lib\asyncio\base_events.py", line 725, in run_until_complete
    return future.result()
           ~~~~~~~~~~~~~^^
  File "C:\dev\F3Next\containers\implementation\is_harness.py", line 483, in _main
    result = await _run_step(
             ^^^^^^^^^^^^^^^^
    ...<4 lines>...
    )
    ^
  File "C:\dev\F3Next\containers\implementation\is_harness.py", line 375, in _run_step
    return await execute_import_phase(ExecutePhaseInput(**fixture))
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\dev\F3Next\containers\implementation\import_agent\activities.py", line 1179, in execute_import_phase
    _pre_resolved_cache, _step_resolution_summaries = await _bulk_pre_resolve_phase_rows(
                                                      ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    ...<5 lines>...
    )
    ^
  File "C:\dev\F3Next\containers\implementation\import_agent\activities.py", line 396, in _bulk_pre_resolve_phase_rows
    rewritten, summary = BulkLinkResolver.apply_resolution_map_to_rows(
                         ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^
        rows,
        ^^^^^
        effective_link_fields,
        ^^^^^^^^^^^^^^^^^^^^^^
        resolution_map,
        ^^^^^^^^^^^^^^^
    )
    ^
  File "C:\dev\F3Next\shared\erp_adapters\link_resolver.py", line 235, in apply_resolution_map_to_rows
    _apply_obj(row)
    ~~~~~~~~~~^^^^^
  File "C:\dev\F3Next\shared\erp_adapters\link_resolver.py", line 214, in _apply_obj
    canonical = resolution_map.resolved.get(target_doctype, {}).get(field_value)
                                            ^^^^^^^^^^^^^^
NameError: name 'target_doctype' is not defined

---

**Cursor**

Pass 2.5 reached real Work Order data — there's a code bug blocking the run. Checking the exact line.


Good progress — you’re on the **right session** now and Pass 2.5 actually ran with real Work Order data. It crashed on a **typo bug** we introduced in `link_resolver.py`.

## What worked

```
🔍    processing step doctype=Work Order          ← real mapped data found
Pass 2.5 — Bulk resolving 3 doctype(s): BOM, Item, Warehouse
BulkLinkResolver: unresolvable Warehouse 'WIP - Factory'
```

So the pipeline is wired correctly. Pass 2.5 fetched live ERPNext data for Item, BOM, and Warehouse before the crash.

## The crash — simple typo bug

In [`shared/erp_adapters/link_resolver.py`](shared/erp_adapters/link_resolver.py) around lines 211–226, the variable is named `target_dt` but the code references `target_doctype`:

```python
target_dt = effective_link_fields.get(field_name)   # line 211 — correct name
...
canonical = resolution_map.resolved.get(target_doctype, {})  # line 214 — WRONG
```

**Fix:** replace all 4 uses of `target_doctype` with `target_dt` inside `_apply_obj` (lines 214, 219, 223, 226).

I'm in Ask mode so I can't edit the file. Switch to **Agent mode** and ask me to fix it, or apply this one-liner yourself:

In `apply_resolution_map_to_rows`, change every `target_doctype` inside `_apply_obj` to `target_dt`.

---

## Secondary finding: `WIP - Factory` still unresolvable

Before the crash, the resolver logged:

```
BulkLinkResolver: unresolvable Warehouse 'WIP - Factory'
```

That means after querying live warehouses from green-surface, **no match was found** — not even via base-name matching (`WIP - *`). Possible reasons:

1. No warehouse named `WIP - GS` (or similar) exists on the site yet  
2. Warehouses use different naming (e.g. `Work In Progress - GS` instead of `WIP - GS`)  
3. Phase A warehouse seeding didn’t create WIP/Stores child warehouses

**Check in ERPNext or via API:**

```sql
-- Or just open ERPNext → Stock → Warehouse list
```

Or after fixing the bug, the logs will show what warehouses were fetched. You can also query:

```
GET /api/resource/Warehouse?fields=["name"]&limit_page_length=50
```

If `WIP - GS` doesn’t exist, Pass 2.5 can’t magic it — you’d need Phase A `seed_from_config` for Warehouse to run first (or create WIP manually in ERPNext).

---

## After fixing the bug — rerun

```powershell
python -m containers.implementation.is_harness --step execute_import_phase --phase phase_c_transactional
```

No need to rerun `finalize_import_plan` — the plan is already wired.

**Expected after fix:**
- Pass 2.5 completes without crash  
- `resolution_summary` in output shows `unresolvable_values` for `wip_warehouse` if WIP warehouse truly doesn’t exist on site  
- Work Order import may still fail with 417 **if** WIP warehouse is missing — but you’ll get a clear log instead of a silent crash

---

## Recommended order

1. **Fix the `target_doctype` → `target_dt` typo** (Agent mode)  
2. **Rerun Phase C harness**  
3. **Check warehouse list on green-surface** — if no WIP warehouse exists, run Phase A first or seed warehouses:

```powershell
python -m containers.implementation.is_harness --step execute_import_phase --phase phase_a_config
```

Then rerun Phase C.

Switch to Agent mode and I can apply the one-line fix and rerun for you.

---

**User**

do the changes you mentioned above

---

**Cursor**

Fixing the `target_doctype` typo and improving warehouse alias matching so `WIP - Factory` resolves to `Work In Progress - GS`.


Done. Here’s what changed and what the rerun showed.

## Fixes applied in `link_resolver.py`

1. **Typo bug** — `target_doctype` → `target_dt` in `apply_resolution_map_to_rows` (this caused the crash).

2. **Warehouse alias matching** — `WIP` now maps to `Work In Progress`, so `WIP - Factory` resolves to `Work In Progress - GS` (matching your ERPNext screenshot, not `WIP - GS`).

## Pass 2.5 — verified working

```
BulkLinkResolver: Warehouse 'WIP - Factory' -> 'Work In Progress - GS'
Pass 2.5: resolved Work Order.wip_warehouse 'WIP - Factory' -> 'Work In Progress - GS'
```

From `phase_c_result.json`:

```json
"resolution_summary": {
  "resolved_count": 2,
  "corrections": [
    {
      "field": "wip_warehouse",
      "original": "WIP - Factory",
      "corrected": "Work In Progress - GS"
    }
  ],
  "unresolvable_values": []
}
```

The original **LinkValidationError on warehouse is fixed**.

## New error (different issue)

Work Orders still failed with:

```
BOM BOM-FG-PRIMER-A-001 must be submitted
```

That’s ERPNext business logic — the BOMs exist as drafts but must be **submitted** (docstatus=1) before a Work Order can be created. That’s separate from link resolution.

**To unblock Work Orders:** submit the BOMs in ERPNext (or add BOM submit to an earlier import phase).

---

You can confirm in ERPNext that the POST no longer mentions `WIP - Factory`; warehouse resolution is handled before the API call. The remaining blocker is BOM submission, not missing warehouses.

---

**User**

now what i should do ?
the IS isnt working with erpnext yet, right ? like it will not work for any data - as we have this new issue in front of us, maybe there are more too

---

**Cursor**

Good question — let me assess how far IS actually gets with ERPNext today and what’s still blocking it.


Your instinct is partly right, but it’s not “IS doesn’t work with ERPNext at all.” It’s more precise to say:

**IS works for simpler paths today. Manufacturing / transactional chains still hit ERPNext business rules the pipeline doesn’t handle yet.**

---

## What you just proved IS *can* do

On Green Surface, session `8a1d1297`:

| Layer | Status |
|---|---|
| Connect to ERPNext API | Works |
| Phase A/B seeding (Currency, Payment Terms, etc.) | Works |
| Read mapped data from R2 | Works |
| Pass 2.5 link resolution (`WIP - Factory` → `Work In Progress - GS`) | **Fixed and verified** |
| POST Work Order to ERPNext | Reaches ERPNext (no more warehouse LinkValidationError) |

So the **integration layer is real** — auth, adapter, import loop, link resolution all function.

---

## Why Work Order still failed (new issue)

```
BOM BOM-FG-PRIMER-A-001 must be submitted
```

In ERPNext:

- **Create** = draft (`docstatus = 0`)
- **Submit** = active (`docstatus = 1`)

Work Orders require a **submitted** BOM. Your IS import only calls `create_record` — it never calls `submit_document`:

```1267:1267:containers/implementation/import_agent/activities.py
                    data = await adapter.create_record(dt, row)
```

The OS agent *does* have submit support; the IS import pipeline does not. So BOMs get created as drafts, then Work Orders fail. That’s **Scenario 5 (rule/state violation)** from the Gemini matrix — not link resolution.

---

## Honest maturity map

| Data type | Likely works today? | Why |
|---|---|---|
| Simple masters (UOM, Territory, Customer Group) | Yes | Few dependencies, no submit required |
| Master records (Customer, Supplier, Item) | Mostly yes | Link resolution helps; some enum/field issues possible |
| Config (Company, Warehouse seed) | Mostly yes | Phase A handles many of these |
| Submittable masters (BOM, Price List with rules) | Partial | Created as draft; downstream docs fail |
| Transactional docs (Work Order, Sales Order, Stock Entry) | Fragile | Need submitted parents + stock + correct state |
| Full manufacturing chain (BOM → WO → Stock Entry) | Not yet | Multiple submit + state dependencies |

So: **IS is not broken end-to-end, but it’s not “any CSV → fully working ERP” yet.** Simple onboarding works better than complex manufacturing flows.

---

## Other issues you’ll likely hit (same class as BOM)

These are the next categories beyond link resolution:

1. **Submit gap** — BOM, Sales Invoice, Purchase Order, Stock Entry often need submit after create  
2. **Ordering gap** — Work Order before BOM is submitted; Delivery Note before Sales Order, etc.  
3. **State gap** — Item must be “Is Stock Item”, BOM item flags, warehouse enabled  
4. **Doctype name mismatch** — Plan says `Work Order (Batch Ticket)` but mapped data is `Work Order` (you saw this earlier)  
5. **Session/plan wiring** — Wrong session = all `data_gap` (also fixed for you now)  
6. **Enum/value mismatches** — e.g. Work Order `status: PASS` vs ERPNext allowed values  

Link resolution fixed **one** failure mode. Manufacturing exposes the **next** layer: ERPNext’s document lifecycle rules.

---

## What you should do now (practical order)

### Option A — Quick unblock (manual, 5 min)

In ERPNext UI for Green Surface:

1. Open `BOM-FG-PRIMER-A-001` and `BOM-FG-PRIMER-B-001`
2. **Submit** both BOMs
3. Re-run Phase C harness:

```powershell
python -m containers.implementation.is_harness --step execute_import_phase --phase phase_c_transactional
```

If Work Orders succeed, you’ve confirmed the **only** remaining blocker was BOM submit — link resolution is done.

### Option B — Test what already works (build confidence)

Run simpler phases on the same session:

```powershell
python -m containers.implementation.is_harness --step execute_import_phase --phase phase_b_master
```

If Customers/Items/BOMs import, IS is working for master data; the gap is specifically transactional/submit logic.

### Option C — Next engineering work (the real fix)

For IS to work reliably on **any** data, the pipeline needs a **document lifecycle layer**:

```
Create → (optional) patch state → Submit → then create child docs
```

Concretely for your case:

1. After BOM `create_record`, call `submit_document("BOM", name)`  
2. Or add a `requires_submit: true` flag in `erpnext_doctype_graph.json` and auto-submit after successful create  
3. Respect phase ordering: BOM fully submitted before Work Order step runs  

That’s a focused next feature — smaller than link resolution, and it unblocks manufacturing.

---

## Bottom line

| Question | Answer |
|---|---|
| Is IS totally broken with ERPNext? | **No** — connection, seeding, mapping, import, link resolution work |
| Will it work for any data? | **Not yet** — especially submittable docs and manufacturing chains |
| Is the warehouse issue fixed? | **Yes** — verified in your last run |
| What’s blocking Work Orders now? | **BOM not submitted** — different class of problem |
| Are there more issues like this? | **Yes** — submit, ordering, state flags; expect them on transactional data |

**Recommended next step:** Manually submit the two BOMs and re-run Phase C. That gives you a clear yes/no on whether link resolution is fully done and submit is the only remaining blocker for this dataset.

If you want, switch to Agent mode and we can add auto-submit for BOM (and other submittable doctypes) as the next IS improvement.

---

**User**

i did submit those 2 BOMs 
and then - 
PS C:\dev\F3Next> python -m containers.implementation.is_harness --step execute_import_phase --phase phase_c_transactional
16:45:00  INFO      is_harness  │
16:45:00  INFO      is_harness  │  ════════════════════════════════════════════════════════════════════════
16:45:00  INFO      is_harness  │    IS STEP HARNESS
16:45:00  INFO      is_harness  │    step     : execute_import_phase
16:45:00  INFO      is_harness  │    mock_llm : False
16:45:00  INFO      is_harness  │    dry_run  : False
16:45:00  INFO      is_harness  │  ════════════════════════════════════════════════════════════════════════
16:45:00  INFO      is_harness  │
16:45:02  INFO      is_harness  │    Fixture  : C:\dev\F3Next\containers\implementation\dev_fixtures\execute_import_phase.json
16:45:02  INFO      is_harness  │    Input    : {"_comment": "Executes one import phase against ERPNext. Use --dry-run to skip actual API writes. Requires build_import_plan to have run first for this session.", "session_id": "8a1d1297-39d3-4b88-82a...
16:45:02  INFO      is_harness  │
16:45:02  INFO      is_harness.activity  │  ▶ execute_import_phase started | session=8a1d1297-39d3-4b88-82a3-cbca4983218b phase=phase_c_transactional dry_run=False
16:45:08  INFO      is_harness.activity  │    🔑 Auto-resolved base_url from Project.deployment_details: https://green-surface.f3next.in
16:45:08  INFO      is_harness.activity  │    🔑 Auto-resolved API credentials from Project.deployment_details
16:45:08  INFO      shared.erp_adapters.erpnext  │  ERPNextAdapter.get_doctype_schema: fetching live schema for Payment Terms Template
16:45:10  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/DocType/Payment%20Terms%20Template "HTTP/1.1 200 OK"
16:45:10  INFO      shared.erp_adapters.erpnext  │  ERPNextAdapter.get_doctype_schema: Payment Terms Template → 3 fields
16:45:10  INFO      shared.erp_adapters.erpnext  │  ERPNextAdapter.get_doctype_schema: fetching live schema for Payment Terms Template Detail
16:45:10  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/DocType/Payment%20Terms%20Template%20Detail "HTTP/1.1 200 OK"
16:45:11  INFO      shared.erp_adapters.erpnext  │  ERPNextAdapter.get_doctype_schema: Payment Terms Template Detail → 11 fields
16:45:11  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22Net+7%22%5D%5D "HTTP/1.1 200 OK"
16:45:12  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22Net+7%22%5D%5D "HTTP/1.1 200 OK"
16:45:12  INFO      shared.erp_adapters.erpnext  │  Record Payment Terms Template 'Net 7' already exists — skipping creation
16:45:13  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22Net+15%22%5D%5D "HTTP/1.1 200 OK"
16:45:13  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22Net+15%22%5D%5D "HTTP/1.1 200 OK"
16:45:13  INFO      shared.erp_adapters.erpnext  │  Record Payment Terms Template 'Net 15' already exists — skipping creation
16:45:13  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22Net+30%22%5D%5D "HTTP/1.1 200 OK"
16:45:13  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22Net+30%22%5D%5D "HTTP/1.1 200 OK"
16:45:13  INFO      shared.erp_adapters.erpnext  │  Record Payment Terms Template 'Net 30' already exists — skipping creation
16:45:13  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22Net+45%22%5D%5D "HTTP/1.1 200 OK"
16:45:14  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22Net+45%22%5D%5D "HTTP/1.1 200 OK"
16:45:14  INFO      shared.erp_adapters.erpnext  │  Record Payment Terms Template 'Net 45' already exists — skipping creation
16:45:14  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22Net+60%22%5D%5D "HTTP/1.1 200 OK"
16:45:14  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22Net+60%22%5D%5D "HTTP/1.1 200 OK"
16:45:14  INFO      shared.erp_adapters.erpnext  │  Record Payment Terms Template 'Net 60' already exists — skipping creation
16:45:14  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22Net+90%22%5D%5D "HTTP/1.1 200 OK"
16:45:14  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22Net+90%22%5D%5D "HTTP/1.1 200 OK"
16:45:14  INFO      shared.erp_adapters.erpnext  │  Record Payment Terms Template 'Net 90' already exists — skipping creation
16:45:14  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22Immediate%22%5D%5D "HTTP/1.1 200 OK"
16:45:15  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22Immediate%22%5D%5D "HTTP/1.1 200 OK"
16:45:15  INFO      shared.erp_adapters.erpnext  │  Record Payment Terms Template 'Immediate' already exists — skipping creation
16:45:15  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22COD%22%5D%5D "HTTP/1.1 200 OK"
16:45:15  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22COD%22%5D%5D "HTTP/1.1 200 OK"
16:45:15  INFO      shared.erp_adapters.erpnext  │  Record Payment Terms Template 'COD' already exists — skipping creation
16:45:15  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22Advance%22%5D%5D "HTTP/1.1 200 OK"
16:45:15  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22Advance%22%5D%5D "HTTP/1.1 200 OK"
16:45:15  INFO      shared.erp_adapters.erpnext  │  Record Payment Terms Template 'Advance' already exists — skipping creation
16:45:15  INFO      is_harness.activity  │    🌱  [SUPP] Payment Terms Template  seeded=9  already_existed=0  failed=0
16:45:15  INFO      is_harness.activity  │
16:45:15  INFO      is_harness.activity  │    🔍  PASS 2 — scanning 3 step(s) for unknown link targets
16:45:15  INFO      is_harness.activity  │    🔍    skip step doctype=Stock Entry action=data_gap (not create)
16:45:15  INFO      is_harness.activity  │    🔍    skip step doctype=Purchase Receipt action=data_gap (not create)
16:45:15  INFO      is_harness.activity  │    🔍    processing step doctype=Work Order
16:45:17  INFO      is_harness.activity  │    🔍  PASS 2 — No unknown link targets found, skipping
16:45:17  INFO      is_harness.activity  │
16:45:17  INFO      is_harness.activity  │    🔗  PASS 2.5 — Bulk link pre-resolution
16:45:17  INFO      is_harness.activity  │    Pass 2.5 — Bulk resolving 3 doctype(s): BOM, Item, Warehouse
16:45:17  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Item?fields=%5B%22name%22%2C+%22disabled%22%5D&limit_page_length=1000&limit_start=0&filters=%5B%5B%22disabled%22%2C+%22%3D%22%2C+0%5D%5D "HTTP/1.1 200 OK"
16:45:18  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/BOM?fields=%5B%22name%22%2C+%22disabled%22%5D&limit_page_length=1000&limit_start=0&filters=%5B%5B%22disabled%22%2C+%22%3D%22%2C+0%5D%5D "HTTP/1.1 417 Expectation Failed"
16:45:18  WARNING   is_harness.activity  │  BulkLinkResolver: disabled-filter fetch failed for BOM: ERPNext error 417: DataError: frappe.exceptions.DataError: Field not permitted in query: disabled
16:45:18  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/BOM?fields=%5B%22name%22%5D&limit_page_length=1000&limit_start=0 "HTTP/1.1 200 OK"
16:45:18  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Warehouse?fields=%5B%22name%22%2C+%22disabled%22%5D&limit_page_length=1000&limit_start=0&filters=%5B%5B%22disabled%22%2C+%22%3D%22%2C+0%5D%5D "HTTP/1.1 200 OK"
16:45:18  INFO      is_harness.activity  │  BulkLinkResolver: Warehouse 'WIP - Factory' -> 'Work In Progress - GS'
16:45:18  INFO      is_harness.activity  │    Pass 2.5: resolved Work Order.wip_warehouse 'WIP - Factory' -> 'Work In Progress - GS'
16:45:18  INFO      is_harness.activity  │    Pass 2.5: resolved Work Order.wip_warehouse 'WIP - Factory' -> 'Work In Progress - GS'
16:45:18  INFO      is_harness.activity  │
16:45:18  WARNING   is_harness.activity  │    ⚠️  DATA GAP: Stock Entry has no mapped data file and no baseline — skipping
16:45:18  WARNING   is_harness.activity  │    ⚠️  DATA GAP: Purchase Receipt has no mapped data file and no baseline — skipping
16:45:18  INFO      shared.erp_adapters.erpnext  │  ERPNextAdapter.get_doctype_schema: fetching live schema for Work Order
16:45:18  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/DocType/Work%20Order "HTTP/1.1 200 OK"
16:45:18  INFO      shared.erp_adapters.erpnext  │  ERPNextAdapter.get_doctype_schema: Work Order → 50 fields
16:45:18  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Item?fields=%5B%22name%22%2C+%22disabled%22%5D&limit_page_length=1000&limit_start=0&filters=%5B%5B%22disabled%22%2C+%22%3D%22%2C+0%5D%5D "HTTP/1.1 200 OK"
16:45:18  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/BOM?fields=%5B%22name%22%2C+%22disabled%22%5D&limit_page_length=1000&limit_start=0&filters=%5B%5B%22disabled%22%2C+%22%3D%22%2C+0%5D%5D "HTTP/1.1 417 Expectation Failed"
16:45:19  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/BOM?fields=%5B%22name%22%5D&limit_page_length=1000&limit_start=0 "HTTP/1.1 200 OK"
16:45:19  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Warehouse?fields=%5B%22name%22%2C+%22disabled%22%5D&limit_page_length=1000&limit_start=0&filters=%5B%5B%22disabled%22%2C+%22%3D%22%2C+0%5D%5D "HTTP/1.1 200 OK"
16:45:19  INFO      shared.erp_adapters.erpnext  │  ERPNextAdapter.get_doctype_schema: fetching live schema for Work Order
16:45:19  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/DocType/Work%20Order "HTTP/1.1 200 OK"
16:45:19  INFO      shared.erp_adapters.erpnext  │  ERPNextAdapter.get_doctype_schema: Work Order → 50 fields
16:45:19  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Work%20Order?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22FG-PRIMER-A%22%5D%5D "HTTP/1.1 200 OK"
16:45:20  INFO      httpx  │  HTTP Request: POST https://green-surface.f3next.in/api/resource/Work%20Order "HTTP/1.1 200 OK"
16:45:20  INFO      shared.erp_adapters.erpnext  │  ERPNextAdapter.get_doctype_schema: fetching live schema for Work Order
16:45:20  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/DocType/Work%20Order "HTTP/1.1 200 OK"
16:45:20  INFO      shared.erp_adapters.erpnext  │  ERPNextAdapter.get_doctype_schema: Work Order → 50 fields
16:45:20  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Work%20Order?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22FG-PRIMER-B%22%5D%5D "HTTP/1.1 200 OK"
16:45:20  INFO      httpx  │  HTTP Request: POST https://green-surface.f3next.in/api/resource/Work%20Order "HTTP/1.1 200 OK"
16:45:22  INFO      is_harness.activity  │  ✅ execute_import_phase done | phase=phase_c_transactional records=2
16:45:22  INFO      is_harness  │
16:45:22  INFO      is_harness  │  ════════════════════════════════════════════════════════════════════════
16:45:22  INFO      is_harness  │    ✅  STEP COMPLETE: execute_import_phase
16:45:22  INFO      is_harness  │  ════════════════════════════════════════════════════════════════════════
16:45:22  INFO      is_harness  │

{
  "phase": "phase_c_transactional",
  "status": "success",
  "steps_completed": 1,
  "steps_failed": 0,
  "records_created": 2,
  "execution_logs": [
    {
      "step": 3,
      "doctype": "Work Order",
      "status": "success",
      "records_attempted": 2,
      "records_succeeded": 2,
      "records_failed": 0,
      "duration_seconds": 2,
      "resolution_summary": {
        "resolved_count": 2,
        "corrections": [
          {
            "field": "wip_warehouse",
            "target_doctype": "Warehouse",
            "original": "WIP - Factory",
            "corrected": "Work In Progress - GS"
          },
          {
            "field": "wip_warehouse",
            "target_doctype": "Warehouse",
            "original": "WIP - Factory",
            "corrected": "Work In Progress - GS"
          }
        ],
        "unresolvable_values": [],
        "ambiguous": {},
        "doctype": "Work Order"
      }
    }
  ]
}

PS C:\dev\F3Next> python -m containers.implementation.is_harness --step execute_import_phase --phase phase_b_master
16:46:47  INFO      is_harness  │
16:46:47  INFO      is_harness  │  ════════════════════════════════════════════════════════════════════════
16:46:47  INFO      is_harness  │    IS STEP HARNESS
16:46:47  INFO      is_harness  │    step     : execute_import_phase
16:46:47  INFO      is_harness  │    mock_llm : False
16:46:47  INFO      is_harness  │    dry_run  : False
16:46:47  INFO      is_harness  │  ════════════════════════════════════════════════════════════════════════
16:46:47  INFO      is_harness  │
16:46:49  INFO      is_harness  │    Fixture  : C:\dev\F3Next\containers\implementation\dev_fixtures\execute_import_phase.json
16:46:49  INFO      is_harness  │    Input    : {"_comment": "Executes one import phase against ERPNext. Use --dry-run to skip actual API writes. Requires build_import_plan to have run first for this session.", "session_id": "8a1d1297-39d3-4b88-82a...
16:46:49  INFO      is_harness  │
16:46:50  INFO      is_harness.activity  │  ▶ execute_import_phase started | session=8a1d1297-39d3-4b88-82a3-cbca4983218b phase=phase_b_master dry_run=False
16:46:55  INFO      is_harness.activity  │    🔑 Auto-resolved base_url from Project.deployment_details: https://green-surface.f3next.in
16:46:55  INFO      is_harness.activity  │    🔑 Auto-resolved API credentials from Project.deployment_details
16:46:56  INFO      shared.erp_adapters.erpnext  │  ERPNextAdapter.get_doctype_schema: fetching live schema for Payment Terms Template
16:46:56  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/DocType/Payment%20Terms%20Template "HTTP/1.1 200 OK"
16:46:56  INFO      shared.erp_adapters.erpnext  │  ERPNextAdapter.get_doctype_schema: Payment Terms Template → 3 fields
16:46:56  INFO      shared.erp_adapters.erpnext  │  ERPNextAdapter.get_doctype_schema: fetching live schema for Payment Terms Template Detail
16:46:56  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/DocType/Payment%20Terms%20Template%20Detail "HTTP/1.1 200 OK"
16:46:56  INFO      shared.erp_adapters.erpnext  │  ERPNextAdapter.get_doctype_schema: Payment Terms Template Detail → 11 fields
16:46:57  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22Net+7%22%5D%5D "HTTP/1.1 200 OK"
16:46:57  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22Net+7%22%5D%5D "HTTP/1.1 200 OK"
16:46:57  INFO      shared.erp_adapters.erpnext  │  Record Payment Terms Template 'Net 7' already exists — skipping creation
16:46:57  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22Net+15%22%5D%5D "HTTP/1.1 200 OK"
16:46:57  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22Net+15%22%5D%5D "HTTP/1.1 200 OK"
16:46:57  INFO      shared.erp_adapters.erpnext  │  Record Payment Terms Template 'Net 15' already exists — skipping creation
16:46:57  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22Net+30%22%5D%5D "HTTP/1.1 200 OK"
16:46:57  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22Net+30%22%5D%5D "HTTP/1.1 200 OK"
16:46:57  INFO      shared.erp_adapters.erpnext  │  Record Payment Terms Template 'Net 30' already exists — skipping creation
16:46:58  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22Net+45%22%5D%5D "HTTP/1.1 200 OK"
16:46:58  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22Net+45%22%5D%5D "HTTP/1.1 200 OK"
16:46:58  INFO      shared.erp_adapters.erpnext  │  Record Payment Terms Template 'Net 45' already exists — skipping creation
16:46:58  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22Net+60%22%5D%5D "HTTP/1.1 200 OK"
16:46:58  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22Net+60%22%5D%5D "HTTP/1.1 200 OK"
16:46:58  INFO      shared.erp_adapters.erpnext  │  Record Payment Terms Template 'Net 60' already exists — skipping creation
16:46:58  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22Net+90%22%5D%5D "HTTP/1.1 200 OK"
16:46:59  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22Net+90%22%5D%5D "HTTP/1.1 200 OK"
16:46:59  INFO      shared.erp_adapters.erpnext  │  Record Payment Terms Template 'Net 90' already exists — skipping creation
16:46:59  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22Immediate%22%5D%5D "HTTP/1.1 200 OK"
16:46:59  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22Immediate%22%5D%5D "HTTP/1.1 200 OK"
16:46:59  INFO      shared.erp_adapters.erpnext  │  Record Payment Terms Template 'Immediate' already exists — skipping creation
16:46:59  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22COD%22%5D%5D "HTTP/1.1 200 OK"
16:46:59  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22COD%22%5D%5D "HTTP/1.1 200 OK"
16:46:59  INFO      shared.erp_adapters.erpnext  │  Record Payment Terms Template 'COD' already exists — skipping creation
16:46:59  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22Advance%22%5D%5D "HTTP/1.1 200 OK"
16:46:59  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22Advance%22%5D%5D "HTTP/1.1 200 OK"
16:46:59  INFO      shared.erp_adapters.erpnext  │  Record Payment Terms Template 'Advance' already exists — skipping creation
16:46:59  INFO      is_harness.activity  │    🌱  [SUPP] Payment Terms Template  seeded=9  already_existed=0  failed=0
16:46:59  INFO      is_harness.activity  │
16:46:59  INFO      is_harness.activity  │    🔍  PASS 2 — scanning 3 step(s) for unknown link targets
16:46:59  INFO      is_harness.activity  │    🔍    processing step doctype=Item
16:47:01  INFO      is_harness.activity  │    🔍    skip step doctype=Supplier action=data_gap (not create)
16:47:01  INFO      is_harness.activity  │    🔍    processing step doctype=BOM
16:47:01  INFO      is_harness.activity  │    🔍  PASS 2 — Dynamic discovery for 2 unknown doctype(s): Item Group, UOM
16:47:01  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Item%20Group?fields=%5B%22name%22%5D&limit_page_length=500&limit_start=0 "HTTP/1.1 200 OK"
16:47:01  INFO      is_harness.activity  │    🔍  Item Group              seeded=0  already_existed=3  failed=0
16:47:01  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/UOM?fields=%5B%22name%22%5D&limit_page_length=500&limit_start=0 "HTTP/1.1 200 OK"
16:47:01  INFO      is_harness.activity  │    🔍  UOM                     seeded=0  already_existed=3  failed=0
16:47:01  INFO      is_harness.activity  │
16:47:01  INFO      is_harness.activity  │    🔗  PASS 2.5 — Bulk link pre-resolution
16:47:02  INFO      is_harness.activity  │    Pass 2.5 — Bulk resolving 3 doctype(s): Item, Item Group, UOM
16:47:02  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Item?fields=%5B%22name%22%2C+%22disabled%22%5D&limit_page_length=1000&limit_start=0&filters=%5B%5B%22disabled%22%2C+%22%3D%22%2C+0%5D%5D "HTTP/1.1 200 OK"
16:47:03  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Item%20Group?fields=%5B%22name%22%2C+%22disabled%22%5D&limit_page_length=1000&limit_start=0&filters=%5B%5B%22disabled%22%2C+%22%3D%22%2C+0%5D%5D "HTTP/1.1 417 Expectation Failed"
16:47:03  WARNING   is_harness.activity  │  BulkLinkResolver: disabled-filter fetch failed for Item Group: ERPNext error 417: DataError: frappe.exceptions.DataError: Field not permitted in query: disabled
16:47:03  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Item%20Group?fields=%5B%22name%22%5D&limit_page_length=1000&limit_start=0 "HTTP/1.1 200 OK"
16:47:03  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/UOM?fields=%5B%22name%22%2C+%22disabled%22%5D&limit_page_length=1000&limit_start=0&filters=%5B%5B%22disabled%22%2C+%22%3D%22%2C+0%5D%5D "HTTP/1.1 417 Expectation Failed"
16:47:03  WARNING   is_harness.activity  │  BulkLinkResolver: disabled-filter fetch failed for UOM: ERPNext error 417: DataError: frappe.exceptions.DataError: Field not permitted in query: disabled
16:47:03  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/UOM?fields=%5B%22name%22%5D&limit_page_length=1000&limit_start=0 "HTTP/1.1 200 OK"
16:47:03  INFO      is_harness.activity  │
16:47:03  INFO      shared.erp_adapters.erpnext  │  ERPNextAdapter.get_doctype_schema: fetching live schema for Item
16:47:03  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/DocType/Item "HTTP/1.1 200 OK"
16:47:03  INFO      shared.erp_adapters.erpnext  │  ERPNextAdapter.get_doctype_schema: Item → 77 fields
16:47:03  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Item%20Group?fields=%5B%22name%22%2C+%22disabled%22%5D&limit_page_length=1000&limit_start=0&filters=%5B%5B%22disabled%22%2C+%22%3D%22%2C+0%5D%5D "HTTP/1.1 417 Expectation Failed"
16:47:04  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Item%20Group?fields=%5B%22name%22%5D&limit_page_length=1000&limit_start=0 "HTTP/1.1 200 OK"
16:47:04  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/UOM?fields=%5B%22name%22%2C+%22disabled%22%5D&limit_page_length=1000&limit_start=0&filters=%5B%5B%22disabled%22%2C+%22%3D%22%2C+0%5D%5D "HTTP/1.1 417 Expectation Failed"
16:47:04  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/UOM?fields=%5B%22name%22%5D&limit_page_length=1000&limit_start=0 "HTTP/1.1 200 OK"
16:47:04  INFO      shared.erp_adapters.erpnext  │  ERPNextAdapter.get_doctype_schema: fetching live schema for Item
16:47:04  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/DocType/Item "HTTP/1.1 200 OK"
16:47:04  INFO      shared.erp_adapters.erpnext  │  ERPNextAdapter.get_doctype_schema: Item → 77 fields
16:47:04  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Item?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22RM-EPOX-LIQ%22%5D%5D "HTTP/1.1 200 OK"
16:47:05  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Item?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22RM-EPOX-LIQ%22%5D%5D "HTTP/1.1 200 OK"
16:47:05  INFO      shared.erp_adapters.erpnext  │  Record Item 'RM-EPOX-LIQ' already exists — skipping creation
16:47:05  INFO      shared.erp_adapters.erpnext  │  ERPNextAdapter.get_doctype_schema: fetching live schema for Item
16:47:05  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/DocType/Item "HTTP/1.1 200 OK"
16:47:05  INFO      shared.erp_adapters.erpnext  │  ERPNextAdapter.get_doctype_schema: Item → 77 fields
16:47:05  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Item?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22RM-PIG-GRY%22%5D%5D "HTTP/1.1 200 OK"
16:47:05  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Item?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22RM-PIG-GRY%22%5D%5D "HTTP/1.1 200 OK"
16:47:05  INFO      shared.erp_adapters.erpnext  │  Record Item 'RM-PIG-GRY' already exists — skipping creation
16:47:05  INFO      shared.erp_adapters.erpnext  │  ERPNextAdapter.get_doctype_schema: fetching live schema for Item
16:47:06  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/DocType/Item "HTTP/1.1 200 OK"
16:47:06  INFO      shared.erp_adapters.erpnext  │  ERPNextAdapter.get_doctype_schema: Item → 77 fields
16:47:06  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Item?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22RM-HARD-AMN%22%5D%5D "HTTP/1.1 200 OK"
16:47:06  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Item?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22RM-HARD-AMN%22%5D%5D "HTTP/1.1 200 OK"
16:47:06  INFO      shared.erp_adapters.erpnext  │  Record Item 'RM-HARD-AMN' already exists — skipping creation
16:47:06  INFO      shared.erp_adapters.erpnext  │  ERPNextAdapter.get_doctype_schema: fetching live schema for Item
16:47:07  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/DocType/Item "HTTP/1.1 200 OK"
16:47:07  INFO      shared.erp_adapters.erpnext  │  ERPNextAdapter.get_doctype_schema: Item → 77 fields
16:47:07  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Item?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22FG-PRIMER-A%22%5D%5D "HTTP/1.1 200 OK"
16:47:07  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Item?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22FG-PRIMER-A%22%5D%5D "HTTP/1.1 200 OK"
16:47:07  INFO      shared.erp_adapters.erpnext  │  Record Item 'FG-PRIMER-A' already exists — skipping creation
16:47:07  INFO      shared.erp_adapters.erpnext  │  ERPNextAdapter.get_doctype_schema: fetching live schema for Item
16:47:07  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/DocType/Item "HTTP/1.1 200 OK"
16:47:07  INFO      shared.erp_adapters.erpnext  │  ERPNextAdapter.get_doctype_schema: Item → 77 fields
16:47:08  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Item?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22FG-PRIMER-B%22%5D%5D "HTTP/1.1 200 OK"
16:47:08  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Item?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22FG-PRIMER-B%22%5D%5D "HTTP/1.1 200 OK"
16:47:08  INFO      shared.erp_adapters.erpnext  │  Record Item 'FG-PRIMER-B' already exists — skipping creation
16:47:08  INFO      shared.erp_adapters.erpnext  │  ERPNextAdapter.get_doctype_schema: fetching live schema for Item
16:47:08  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/DocType/Item "HTTP/1.1 200 OK"
16:47:08  INFO      shared.erp_adapters.erpnext  │  ERPNextAdapter.get_doctype_schema: Item → 77 fields
16:47:08  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Item?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22SRV-INSTALL%22%5D%5D "HTTP/1.1 200 OK"
16:47:08  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Item?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22SRV-INSTALL%22%5D%5D "HTTP/1.1 200 OK"
16:47:08  INFO      shared.erp_adapters.erpnext  │  Record Item 'SRV-INSTALL' already exists — skipping creation
16:47:09  WARNING   is_harness.activity  │    ⚠️  DATA GAP: Supplier has no mapped data file and no baseline — skipping
16:47:09  INFO      shared.erp_adapters.erpnext  │  ERPNextAdapter.get_doctype_schema: fetching live schema for BOM
16:47:09  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/DocType/BOM "HTTP/1.1 200 OK"
16:47:09  INFO      shared.erp_adapters.erpnext  │  ERPNextAdapter.get_doctype_schema: BOM → 50 fields
16:47:10  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Item?fields=%5B%22name%22%2C+%22disabled%22%5D&limit_page_length=1000&limit_start=0&filters=%5B%5B%22disabled%22%2C+%22%3D%22%2C+0%5D%5D "HTTP/1.1 200 OK"
16:47:10  INFO      shared.erp_adapters.erpnext  │  ERPNextAdapter.get_doctype_schema: fetching live schema for BOM Item
16:47:10  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/DocType/BOM%20Item "HTTP/1.1 200 OK"
16:47:10  INFO      shared.erp_adapters.erpnext  │  ERPNextAdapter.get_doctype_schema: BOM Item → 25 fields
16:47:10  INFO      shared.erp_adapters.erpnext  │  ERPNextAdapter.get_doctype_schema: fetching live schema for BOM
16:47:10  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/DocType/BOM "HTTP/1.1 200 OK"
16:47:10  INFO      shared.erp_adapters.erpnext  │  ERPNextAdapter.get_doctype_schema: BOM → 50 fields
16:47:10  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/BOM?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22FG-PRIMER-A%22%5D%5D "HTTP/1.1 200 OK"
16:47:10  INFO      httpx  │  HTTP Request: POST https://green-surface.f3next.in/api/resource/BOM "HTTP/1.1 200 OK"
16:47:10  INFO      shared.erp_adapters.erpnext  │  ERPNextAdapter.get_doctype_schema: fetching live schema for BOM
16:47:11  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/DocType/BOM "HTTP/1.1 200 OK"
16:47:11  INFO      shared.erp_adapters.erpnext  │  ERPNextAdapter.get_doctype_schema: BOM → 50 fields
16:47:11  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/BOM?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22FG-PRIMER-B%22%5D%5D "HTTP/1.1 200 OK"
16:47:11  INFO      httpx  │  HTTP Request: POST https://green-surface.f3next.in/api/resource/BOM "HTTP/1.1 200 OK"
16:47:13  INFO      is_harness.activity  │  ✅ execute_import_phase done | phase=phase_b_master records=8
16:47:13  INFO      is_harness  │
16:47:13  INFO      is_harness  │  ════════════════════════════════════════════════════════════════════════
16:47:13  INFO      is_harness  │    ✅  STEP COMPLETE: execute_import_phase
16:47:13  INFO      is_harness  │  ════════════════════════════════════════════════════════════════════════
16:47:13  INFO      is_harness  │

{
  "phase": "phase_b_master",
  "status": "success",
  "steps_completed": 2,
  "steps_failed": 0,
  "records_created": 8,
  "execution_logs": [
    {
      "step": 1,
      "doctype": "Item",
      "status": "success",
      "records_attempted": 6,
      "records_succeeded": 6,
      "records_failed": 0,
      "duration_seconds": 5,
      "resolution_summary": {
        "resolved_count": 0,
        "corrections": [],
        "unresolvable_values": [],
        "ambiguous": {},
        "doctype": "Item"
      }
    },
    {
      "step": 3,
      "doctype": "BOM",
      "status": "success",
      "records_attempted": 2,
      "records_succeeded": 2,
      "records_failed": 0,
      "duration_seconds": 2,
      "resolution_summary": {
        "resolved_count": 0,
        "corrections": [],
        "unresolvable_values": [],
        "ambiguous": {},
        "doctype": "BOM"
      }
    }
  ]
}

---

**Cursor**

**Phase C succeeded.** That’s the important result — your Green Surface manufacturing path is working end-to-end for what you have mapped.

---

## What just worked

| Phase | Result | Details |
|---|---|---|
| **Phase C** | ✅ Success | 2 Work Orders created (`FG-PRIMER-A`, `FG-PRIMER-B`) |
| **Link resolution** | ✅ Working | `WIP - Factory` → `Work In Progress - GS` (both rows) |
| **Phase B** | ✅ Success | 6 Items skipped (already exist), 2 BOMs created |
| **BOM submit blocker** | ✅ Resolved | Manual submit unblocked Work Orders |

So IS **does work with ERPNext** for this dataset — not “broken for all data,” but **working for the mapped slice you’ve tested**.

---

## What was skipped (expected, not failures)

These are **data gaps**, not import bugs:

| Doctype | Phase | Why skipped |
|---|---|---|
| Stock Entry | C | No mapped file for this session |
| Purchase Receipt | C | No mapped file |
| Supplier | B | No mapped file |

The import plan includes them, but there’s no CSV/data linked — IS correctly skips with `DATA GAP`.

---

## One thing to verify in ERPNext UI

Open **Manufacturing → Work Order** on Green Surface and confirm:

- `FG-PRIMER-A` and `FG-PRIMER-B` exist
- `wip_warehouse` = **Work In Progress - GS**
- Linked BOMs are the **submitted** ones (`BOM-FG-PRIMER-A-001`, etc.)

Also check **BOM** — your Phase B re-run may have created **new draft BOMs** named `FG-PRIMER-A` / `FG-PRIMER-B` (different from `BOM-FG-PRIMER-A-001`). That happens because existence check uses item name, not your submitted BOM names. Not blocking now, but worth cleaning up duplicates in ERPNext if you see them.

---

## Updated maturity picture

For **Green Surface + this session**, you now have proof of:

```
Phase A seeds (Payment Terms, etc.)     ✅
Phase B masters (Item, BOM)             ✅  (Supplier gap)
Phase C transactional (Work Order)      ✅  (Stock Entry / PR gap)
Pass 2.5 link resolution                ✅
Manual BOM submit as prerequisite         ⚠️  still required today
```

IS is **not** “won’t work for any data.” It’s:

- **Works** for simple masters + your manufacturing WO path (with known prerequisites)
- **Skips** doctypes with no uploaded/mapped data
- **Still needs engineering** for full autonomy (auto-submit, more doctypes, more ERPNext rules)

---

## What you should do next (in order)

### 1. Sanity-check ERPNext (5 min)
Confirm Work Orders look correct in the UI. That closes the loop on this test.

### 2. Decide scope for “done” on this branch
You’ve validated the link-resolution fix. Good next moves:

- **Commit** `link_resolver.py`, `activities.py`, `erpnext.py` fixes (if not committed yet)
- **Open a PR** for `feature/is-link-resolution-v2` with test notes from this run

### 3. Next engineering item (when you’re ready)
**Auto-submit after BOM create** — so the next customer doesn’t need manual submit before Work Orders. Small, high-value change in the import loop.

### 4. Optional: expand coverage
If you want a fuller Green Surface import:

- Upload/map **Supplier**, **Stock Entry**, **Purchase Receipt**
- Re-run `build_import_plan` → `finalize_import_plan` → execute phases again

### 5. Optional: run Phase A
If you haven’t recently:

```powershell
python -m containers.implementation.is_harness --step execute_import_phase --phase phase_a_universal
```

Mostly idempotent (skips existing records).

---

## Minor noise in logs (not blockers)

The `417 Field not permitted: disabled` warnings on **BOM**, **Item Group**, **UOM** are handled — code falls back to name-only fetch and continues. Worth a cleanup later (don’t query `disabled` on doctypes that don’t support it), but not urgent.

---

## Bottom line

You’re past “IS doesn’t work with ERPNext.” For Green Surface you’ve proven:

1. Link resolution fixes real warehouse mismatches  
2. Work Orders import once BOMs are submitted  
3. Phase B masters are stable (idempotent re-runs)

**Immediate action:** Check Work Orders in ERPNext UI, then commit/PR the link-resolution work. **Next feature:** auto-submit for BOM (and similar submittable doctypes) so you don’t need the manual step again.

If you want help implementing auto-submit or cleaning up the BOM duplicate naming issue, switch to Agent mode and we can do that next.

---

**User**

commit the changes !
and then write a plan that talks about the submit issue and other issues that might occur, and the gaps in our IS and OS or in our project !
also write any new idea you think we should add, or any new thing like harness for random requests by user - for example - asking user before submitting, warnings for financial actions etc.

---

**Cursor**

Gathering git state and codebase context for the commit and the broader IS/OS gaps plan.


I have enough context: one commit is pending on top of `af11915`, and the broader roadmap should cover submit/lifecycle gaps plus safety harness ideas.


**Commit scope**

> **For dev_fixtures/execute_import_phase.json: commit session_id update but keep dry_run safe?**
> - Commit session_id only; revert dry_run back to true (safer default for shared repo) ✔
> - Commit both session_id and dry_run: false (Green Surface live-test default)

---

**User**

Implement the plan as specified, it is attached for your reference. Do NOT edit the plan file itself.

To-do's from the plan have already been created. Do not create them again. Mark them as in_progress as you work, starting with the first one. Don't stop until you have completed all the to-dos.

---

**Cursor**

Implementing the roadmap: starting with the commit, then working through each todo systematically.


Implementing core modules and adapter fixes.


All plan todos are done. Two commits on `feature/is-link-resolution-v2`:

1. **`9f8e6ff`** — link resolver aliases + dev fixtures  
2. **`137dfc8`** — document lifecycle, preflight gate, OS action harness  

---

## What was implemented

### Document lifecycle (Pass 2.6)
- After each successful `create_record`, IS checks KB lifecycle policy and auto-submits when configured
- **BOM** auto-submits by default (no more manual submit before Work Orders)
- `submit_summary` added to execution logs alongside `resolution_summary`

### Submit API fix
- `submit_document` now uses `POST /api/method/frappe.client.submit` with PUT `docstatus=1` fallback

### BOM idempotency
- Existence check by **`item` + `company`**, not just `name` — avoids duplicate BOMs on re-run

### Shared policy module (`shared/erp_policies/`)
- **`lifecycle.py`** — KB-driven `auto_submit_on_import`, risk tiers, disabled-filter allowlist  
- **`action_risk.py`** — risk classification + confirmation preview builder for IS and OS

### Preflight harness
```powershell
python -m containers.implementation.is_harness --step preflight_import --phase phase_c_transactional
```
Read-only report: link corrections, draft BOMs, financial warnings, data gaps.

### Execution gate (Phase B/C)
- `execute_import_phase` returns `awaiting_confirmation` unless `execution_confirmed` or `skip_execution_gate`
- Supervisor node `execute_import_phase` prompts: *"Confirm and run import"*
- Workflow runs preflight + supervisor gate when `IS_SUPERVISOR_ENABLED=1`
- Harness bypass: `--confirm-execution`

### OS action harness
```powershell
python -m containers.os.action_harness --intent "create sales order for Acme" --preview-only
python -m containers.os.action_harness --intent "..." --confirm --project-id b6ff0b7f-...
```

---

## How to test Green Surface end-to-end (no manual BOM submit)

```powershell
# 1. Preflight (read-only)
python -m containers.implementation.is_harness --step preflight_import --phase phase_b_master

# 2. Phase B — BOMs should auto-submit
python -m containers.implementation.is_harness --step execute_import_phase --phase phase_b_master --confirm-execution

# 3. Phase C — Work Orders without manual BOM submit
python -m containers.implementation.is_harness --step execute_import_phase --phase phase_c_transactional --confirm-execution
```

Check logs for `Pass 2.6: submitted BOM` and `submit_summary` in the JSON result.

---

**User**

now - are we still erp and industry agnostic ?
and how to do the tests now ?
btw have we also built the part 4,5,6 too - those were new ideas right ?

---

**Cursor**

Checking what's implemented versus what's still aspirational, and how agnostic the design remains.


Good questions. Here’s an honest read of where things stand after the roadmap work (commits `9f8e6ff` and `137dfc8` on `feature/is-link-resolution-v2`).

---

## 1. Are we still ERP- and industry-agnostic?

**In architecture: partially. In practice today: no — we’re ERPNext-first, industry-flexible.**

| Layer | Agnostic? | Reality |
|---|---|---|
| **Adapter interface** | Yes | `ERPAdapter` + `get_adapter()` still abstract CRUD/submit/list |
| **Supported ERPs** | No | Registry only implements `erpnext` — anything else raises `Unsupported erp_type` |
| **IS import pipeline** | ERPNext-shaped | Doctypes, phases, `frappe.client.submit`, link resolution all assume ERPNext API + naming |
| **Industry** | Flexible at intake | F3ICHE, playbooks, target agent still adapt to manufacturing/trading/etc. |
| **New lifecycle/risk code** | KB-driven in design | Hardcoded ERPNext doctypes in `_BUILTIN_LIFECYCLE` (BOM, Sales Invoice, etc.) and `erpnext_doctype_graph.json` |

So:

- **Industry-agnostic** at the *onboarding story* level (upload files → map → plan → import varies by F3ICHE/playbooks).
- **Not ERP-agnostic** yet — another ERP would need a new adapter, lifecycle graph, submit semantics, and doctype model.
- **Not fully industry-neutral in code** — Green Surface/manufacturing leaks in (WIP/FG warehouse aliases, BOM→Work Order chain, Work Order enum fixes).

The plan’s direction (KB-driven lifecycle in Part 4e) *supports* future agnosticism, but we haven’t externalized everything to KB yet — `_BUILTIN_LIFECYCLE` and link aliases are still code-level ERPNext/manufacturing shortcuts.

---

## 2. Did we build Part 4, 5, and 6?

The plan has three different kinds of sections:

### Part 4 — New ideas → **Mostly built as code**

| Idea | Built? | Where |
|---|---|---|
| **4a** Import execution gate | Yes | `execute_import_phase` gate, supervisor `execute_import_phase` node, workflow preflight + wait |
| **4b** `preflight_import` harness | Yes | `preflight_import` activity + `is_harness --step preflight_import` |
| **4c** OS `action_harness` | Yes | `containers/os/action_harness.py` |
| **4d** Shared `action_risk` | Yes | `shared/erp_policies/action_risk.py` (used by IS preflight + OS execution) |
| **4e** KB lifecycle config | **Partial** | BOM + Work Order in `erpnext_doctype_graph.json`; rest in `_BUILTIN_LIFECYCLE` fallback |
| **4f** `.gitignore` hygiene | Yes | `phase_c_result.json`, `*_harness_result.json` ignored |

### Part 5 — Implementation order → **That was the build checklist**

All P0–P8 items from Part 5 were implemented in the previous Agent session (commit, submit API, Pass 2.6, preflight, gate, action_risk, BOM dedup, disabled allowlist, action_harness).

### Part 6 — Success criteria → **Not “code to build” — it’s your test checklist**

Part 6 defines *when Green Surface manufacturing MVP is truly done*. You still need to **run** those checks; they aren’t automatically verified.

---

## 3. How to test now

Use session `8a1d1297-...` and project `b6ff0b7f-...` (Green Surface fixtures already point there).

### Step 0 — Preflight (read-only, no writes)

```powershell
python -m containers.implementation.is_harness --step preflight_import --phase phase_b_master
python -m containers.implementation.is_harness --step preflight_import --phase phase_c_transactional
```

Check JSON for:
- `link_corrections` (e.g. WIP → Work In Progress - GS)
- `draft_parents` (draft BOMs blocking Work Orders)
- `requires_execution_gate`
- `warnings` for financial/high-risk doctypes

### Step 1 — Phase B (Items + BOMs, with auto-submit)

Harness defaults to `dry_run: true` in fixture — for live writes:

```powershell
python -m containers.implementation.is_harness --step execute_import_phase --phase phase_b_master --confirm-execution
```

**Look for in logs:**
- `Pass 2.6: submitted BOM '...'`
- `submit_summary` in result JSON with `"action": "submitted"`
- No duplicate BOMs (item-level dedup should skip existing)

### Step 2 — Phase C (Work Orders)

```powershell
python -m containers.implementation.is_harness --step execute_import_phase --phase phase_c_transactional --confirm-execution
```

**Look for:**
- `resolution_summary` warehouse corrections
- Work Orders created without manual BOM submit in ERPNext UI
- `status: "success"`, `records_created: 2`

### Step 3 — Idempotency re-run

Re-run Phase B and C with `--confirm-execution`. Items/BOMs should skip or no-op; no new duplicate BOM names.

### Step 4 — OS action harness (ad-hoc)

```powershell
python -m containers.os.action_harness --intent "list open work orders" --project-id b6ff0b7f-a616-4179-8f68-deda9b3578af --preview-only
```

Add `--confirm` only when preview looks correct and you accept live writes.

### Step 5 — Full workflow (Temporal UI)

If testing via Docker worker, **rebuild `implementation_worker`** so it picks up new activities (`preflight_import`, Pass 2.6). Set `IS_SUPERVISOR_ENABLED=1` to exercise the execution gate in the UI before Phase B/C.

### Part 6 checklist mapping

| Criterion | How to verify |
|---|---|
| Phase B BOMs submitted automatically | Logs + ERPNext UI docstatus=1 |
| Phase C Work Orders + warehouse resolve | Harness result + ERPNext UI |
| Re-run idempotent | Second run, no duplicate BOMs |
| Preflight zero blockers | `preflight_import` JSON before live run |
| Both summaries in logs | `resolution_summary` + `submit_summary` in execution_logs |

---

## Bottom line

- **Plan implementation:** Parts 4 (mostly) and 5 (all) are in the branch. Part 6 is your manual acceptance test, not missing code.
- **Agnosticism:** Pipeline shape is reusable; runtime is **ERPNext + manufacturing-biased** until another adapter/KB graph exists and hardcoded aliases/builtins move to config.
- **Next practical step:** Run preflight → Phase B with `--confirm-execution` → Phase C, and confirm `Pass 2.6` + Work Orders without manual BOM submit.

If you want me to run those tests or push/open the PR, switch to **Agent mode** and say so.

---

**User**

runs :
PS C:\dev\F3Next> python -m containers.implementation.is_harness --step execute_import_phase --phase phase_b_master
16:46:47  INFO      is_harness  │
16:46:47  INFO      is_harness  │  ════════════════════════════════════════════════════════════════════════
16:46:47  INFO      is_harness  │    IS STEP HARNESS
16:46:47  INFO      is_harness  │    step     : execute_import_phase
16:46:47  INFO      is_harness  │    mock_llm : False
16:46:47  INFO      is_harness  │    dry_run  : False
16:46:47  INFO      is_harness  │  ════════════════════════════════════════════════════════════════════════
16:46:47  INFO      is_harness  │
16:46:49  INFO      is_harness  │    Fixture  : C:\dev\F3Next\containers\implementation\dev_fixtures\execute_import_phase.json
16:46:49  INFO      is_harness  │    Input    : {"_comment": "Executes one import phase against ERPNext. Use --dry-run to skip actual API writes. Requires build_import_plan to have run first for this session.", "session_id": "8a1d1297-39d3-4b88-82a...
16:46:49  INFO      is_harness  │
16:46:50  INFO      is_harness.activity  │  ▶ execute_import_phase started | session=8a1d1297-39d3-4b88-82a3-cbca4983218b phase=phase_b_master dry_run=False
16:46:55  INFO      is_harness.activity  │    🔑 Auto-resolved base_url from Project.deployment_details: https://green-surface.f3next.in
16:46:55  INFO      is_harness.activity  │    🔑 Auto-resolved API credentials from Project.deployment_details
16:46:56  INFO      shared.erp_adapters.erpnext  │  ERPNextAdapter.get_doctype_schema: fetching live schema for Payment Terms Template
16:46:56  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/DocType/Payment%20Terms%20Template "HTTP/1.1 200 OK"
16:46:56  INFO      shared.erp_adapters.erpnext  │  ERPNextAdapter.get_doctype_schema: Payment Terms Template → 3 fields
16:46:56  INFO      shared.erp_adapters.erpnext  │  ERPNextAdapter.get_doctype_schema: fetching live schema for Payment Terms Template Detail
16:46:56  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/DocType/Payment%20Terms%20Template%20Detail "HTTP/1.1 200 OK"
16:46:56  INFO      shared.erp_adapters.erpnext  │  ERPNextAdapter.get_doctype_schema: Payment Terms Template Detail → 11 fields
16:46:57  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22Net+7%22%5D%5D "HTTP/1.1 200 OK"
16:46:57  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22Net+7%22%5D%5D "HTTP/1.1 200 OK"
16:46:57  INFO      shared.erp_adapters.erpnext  │  Record Payment Terms Template 'Net 7' already exists — skipping creation
16:46:57  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22Net+15%22%5D%5D "HTTP/1.1 200 OK"
16:46:57  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22Net+15%22%5D%5D "HTTP/1.1 200 OK"
16:46:57  INFO      shared.erp_adapters.erpnext  │  Record Payment Terms Template 'Net 15' already exists — skipping creation
16:46:57  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22Net+30%22%5D%5D "HTTP/1.1 200 OK"
16:46:57  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22Net+30%22%5D%5D "HTTP/1.1 200 OK"
16:46:57  INFO      shared.erp_adapters.erpnext  │  Record Payment Terms Template 'Net 30' already exists — skipping creation
16:46:58  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22Net+45%22%5D%5D "HTTP/1.1 200 OK"
16:46:58  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22Net+45%22%5D%5D "HTTP/1.1 200 OK"
16:46:58  INFO      shared.erp_adapters.erpnext  │  Record Payment Terms Template 'Net 45' already exists — skipping creation
16:46:58  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22Net+60%22%5D%5D "HTTP/1.1 200 OK"
16:46:58  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22Net+60%22%5D%5D "HTTP/1.1 200 OK"
16:46:58  INFO      shared.erp_adapters.erpnext  │  Record Payment Terms Template 'Net 60' already exists — skipping creation
16:46:58  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22Net+90%22%5D%5D "HTTP/1.1 200 OK"
16:46:59  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22Net+90%22%5D%5D "HTTP/1.1 200 OK"
16:46:59  INFO      shared.erp_adapters.erpnext  │  Record Payment Terms Template 'Net 90' already exists — skipping creation
16:46:59  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22Immediate%22%5D%5D "HTTP/1.1 200 OK"
16:46:59  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22Immediate%22%5D%5D "HTTP/1.1 200 OK"
16:46:59  INFO      shared.erp_adapters.erpnext  │  Record Payment Terms Template 'Immediate' already exists — skipping creation
16:46:59  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22COD%22%5D%5D "HTTP/1.1 200 OK"
16:46:59  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22COD%22%5D%5D "HTTP/1.1 200 OK"
16:46:59  INFO      shared.erp_adapters.erpnext  │  Record Payment Terms Template 'COD' already exists — skipping creation
16:46:59  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22Advance%22%5D%5D "HTTP/1.1 200 OK"
16:46:59  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Payment%20Terms%20Template?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22Advance%22%5D%5D "HTTP/1.1 200 OK"
16:46:59  INFO      shared.erp_adapters.erpnext  │  Record Payment Terms Template 'Advance' already exists — skipping creation
16:46:59  INFO      is_harness.activity  │    🌱  [SUPP] Payment Terms Template  seeded=9  already_existed=0  failed=0
16:46:59  INFO      is_harness.activity  │
16:46:59  INFO      is_harness.activity  │    🔍  PASS 2 — scanning 3 step(s) for unknown link targets
16:46:59  INFO      is_harness.activity  │    🔍    processing step doctype=Item
16:47:01  INFO      is_harness.activity  │    🔍    skip step doctype=Supplier action=data_gap (not create)
16:47:01  INFO      is_harness.activity  │    🔍    processing step doctype=BOM
16:47:01  INFO      is_harness.activity  │    🔍  PASS 2 — Dynamic discovery for 2 unknown doctype(s): Item Group, UOM
16:47:01  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Item%20Group?fields=%5B%22name%22%5D&limit_page_length=500&limit_start=0 "HTTP/1.1 200 OK"
16:47:01  INFO      is_harness.activity  │    🔍  Item Group              seeded=0  already_existed=3  failed=0
16:47:01  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/UOM?fields=%5B%22name%22%5D&limit_page_length=500&limit_start=0 "HTTP/1.1 200 OK"
16:47:01  INFO      is_harness.activity  │    🔍  UOM                     seeded=0  already_existed=3  failed=0
16:47:01  INFO      is_harness.activity  │
16:47:01  INFO      is_harness.activity  │    🔗  PASS 2.5 — Bulk link pre-resolution
16:47:02  INFO      is_harness.activity  │    Pass 2.5 — Bulk resolving 3 doctype(s): Item, Item Group, UOM
16:47:02  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Item?fields=%5B%22name%22%2C+%22disabled%22%5D&limit_page_length=1000&limit_start=0&filters=%5B%5B%22disabled%22%2C+%22%3D%22%2C+0%5D%5D "HTTP/1.1 200 OK"
16:47:03  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Item%20Group?fields=%5B%22name%22%2C+%22disabled%22%5D&limit_page_length=1000&limit_start=0&filters=%5B%5B%22disabled%22%2C+%22%3D%22%2C+0%5D%5D "HTTP/1.1 417 Expectation Failed"
16:47:03  WARNING   is_harness.activity  │  BulkLinkResolver: disabled-filter fetch failed for Item Group: ERPNext error 417: DataError: frappe.exceptions.DataError: Field not permitted in query: disabled
16:47:03  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Item%20Group?fields=%5B%22name%22%5D&limit_page_length=1000&limit_start=0 "HTTP/1.1 200 OK"
16:47:03  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/UOM?fields=%5B%22name%22%2C+%22disabled%22%5D&limit_page_length=1000&limit_start=0&filters=%5B%5B%22disabled%22%2C+%22%3D%22%2C+0%5D%5D "HTTP/1.1 417 Expectation Failed"
16:47:03  WARNING   is_harness.activity  │  BulkLinkResolver: disabled-filter fetch failed for UOM: ERPNext error 417: DataError: frappe.exceptions.DataError: Field not permitted in query: disabled
16:47:03  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/UOM?fields=%5B%22name%22%5D&limit_page_length=1000&limit_start=0 "HTTP/1.1 200 OK"
16:47:03  INFO      is_harness.activity  │
16:47:03  INFO      shared.erp_adapters.erpnext  │  ERPNextAdapter.get_doctype_schema: fetching live schema for Item
16:47:03  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/DocType/Item "HTTP/1.1 200 OK"
16:47:03  INFO      shared.erp_adapters.erpnext  │  ERPNextAdapter.get_doctype_schema: Item → 77 fields
16:47:03  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Item%20Group?fields=%5B%22name%22%2C+%22disabled%22%5D&limit_page_length=1000&limit_start=0&filters=%5B%5B%22disabled%22%2C+%22%3D%22%2C+0%5D%5D "HTTP/1.1 417 Expectation Failed"
16:47:04  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Item%20Group?fields=%5B%22name%22%5D&limit_page_length=1000&limit_start=0 "HTTP/1.1 200 OK"
16:47:04  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/UOM?fields=%5B%22name%22%2C+%22disabled%22%5D&limit_page_length=1000&limit_start=0&filters=%5B%5B%22disabled%22%2C+%22%3D%22%2C+0%5D%5D "HTTP/1.1 417 Expectation Failed"
16:47:04  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/UOM?fields=%5B%22name%22%5D&limit_page_length=1000&limit_start=0 "HTTP/1.1 200 OK"
16:47:04  INFO      shared.erp_adapters.erpnext  │  ERPNextAdapter.get_doctype_schema: fetching live schema for Item
16:47:04  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/DocType/Item "HTTP/1.1 200 OK"
16:47:04  INFO      shared.erp_adapters.erpnext  │  ERPNextAdapter.get_doctype_schema: Item → 77 fields
16:47:04  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Item?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22RM-EPOX-LIQ%22%5D%5D "HTTP/1.1 200 OK"
16:47:05  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Item?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22RM-EPOX-LIQ%22%5D%5D "HTTP/1.1 200 OK"
16:47:05  INFO      shared.erp_adapters.erpnext  │  Record Item 'RM-EPOX-LIQ' already exists — skipping creation
16:47:05  INFO      shared.erp_adapters.erpnext  │  ERPNextAdapter.get_doctype_schema: fetching live schema for Item
16:47:05  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/DocType/Item "HTTP/1.1 200 OK"
16:47:05  INFO      shared.erp_adapters.erpnext  │  ERPNextAdapter.get_doctype_schema: Item → 77 fields
16:47:05  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Item?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22RM-PIG-GRY%22%5D%5D "HTTP/1.1 200 OK"
16:47:05  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Item?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22RM-PIG-GRY%22%5D%5D "HTTP/1.1 200 OK"
16:47:05  INFO      shared.erp_adapters.erpnext  │  Record Item 'RM-PIG-GRY' already exists — skipping creation
16:47:05  INFO      shared.erp_adapters.erpnext  │  ERPNextAdapter.get_doctype_schema: fetching live schema for Item
16:47:06  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/DocType/Item "HTTP/1.1 200 OK"
16:47:06  INFO      shared.erp_adapters.erpnext  │  ERPNextAdapter.get_doctype_schema: Item → 77 fields
16:47:06  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Item?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22RM-HARD-AMN%22%5D%5D "HTTP/1.1 200 OK"
16:47:06  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Item?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22RM-HARD-AMN%22%5D%5D "HTTP/1.1 200 OK"
16:47:06  INFO      shared.erp_adapters.erpnext  │  Record Item 'RM-HARD-AMN' already exists — skipping creation
16:47:06  INFO      shared.erp_adapters.erpnext  │  ERPNextAdapter.get_doctype_schema: fetching live schema for Item
16:47:07  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/DocType/Item "HTTP/1.1 200 OK"
16:47:07  INFO      shared.erp_adapters.erpnext  │  ERPNextAdapter.get_doctype_schema: Item → 77 fields
16:47:07  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Item?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22FG-PRIMER-A%22%5D%5D "HTTP/1.1 200 OK"
16:47:07  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Item?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22FG-PRIMER-A%22%5D%5D "HTTP/1.1 200 OK"
16:47:07  INFO      shared.erp_adapters.erpnext  │  Record Item 'FG-PRIMER-A' already exists — skipping creation
16:47:07  INFO      shared.erp_adapters.erpnext  │  ERPNextAdapter.get_doctype_schema: fetching live schema for Item
16:47:07  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/DocType/Item "HTTP/1.1 200 OK"
16:47:07  INFO      shared.erp_adapters.erpnext  │  ERPNextAdapter.get_doctype_schema: Item → 77 fields
16:47:08  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Item?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22FG-PRIMER-B%22%5D%5D "HTTP/1.1 200 OK"
16:47:08  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Item?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22FG-PRIMER-B%22%5D%5D "HTTP/1.1 200 OK"
16:47:08  INFO      shared.erp_adapters.erpnext  │  Record Item 'FG-PRIMER-B' already exists — skipping creation
16:47:08  INFO      shared.erp_adapters.erpnext  │  ERPNextAdapter.get_doctype_schema: fetching live schema for Item
16:47:08  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/DocType/Item "HTTP/1.1 200 OK"
16:47:08  INFO      shared.erp_adapters.erpnext  │  ERPNextAdapter.get_doctype_schema: Item → 77 fields
16:47:08  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Item?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22SRV-INSTALL%22%5D%5D "HTTP/1.1 200 OK"
16:47:08  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Item?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=1&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22SRV-INSTALL%22%5D%5D "HTTP/1.1 200 OK"
16:47:08  INFO      shared.erp_adapters.erpnext  │  Record Item 'SRV-INSTALL' already exists — skipping creation
16:47:09  WARNING   is_harness.activity  │    ⚠️  DATA GAP: Supplier has no mapped data file and no baseline — skipping
16:47:09  INFO      shared.erp_adapters.erpnext  │  ERPNextAdapter.get_doctype_schema: fetching live schema for BOM
16:47:09  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/DocType/BOM "HTTP/1.1 200 OK"
16:47:09  INFO      shared.erp_adapters.erpnext  │  ERPNextAdapter.get_doctype_schema: BOM → 50 fields
16:47:10  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Item?fields=%5B%22name%22%2C+%22disabled%22%5D&limit_page_length=1000&limit_start=0&filters=%5B%5B%22disabled%22%2C+%22%3D%22%2C+0%5D%5D "HTTP/1.1 200 OK"
16:47:10  INFO      shared.erp_adapters.erpnext  │  ERPNextAdapter.get_doctype_schema: fetching live schema for BOM Item
16:47:10  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/DocType/BOM%20Item "HTTP/1.1 200 OK"
16:47:10  INFO      shared.erp_adapters.erpnext  │  ERPNextAdapter.get_doctype_schema: BOM Item → 25 fields
16:47:10  INFO      shared.erp_adapters.erpnext  │  ERPNextAdapter.get_doctype_schema: fetching live schema for BOM
16:47:10  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/DocType/BOM "HTTP/1.1 200 OK"
16:47:10  INFO      shared.erp_adapters.erpnext  │  ERPNextAdapter.get_doctype_schema: BOM → 50 fields
16:47:10  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/BOM?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22FG-PRIMER-A%22%5D%5D "HTTP/1.1 200 OK"
16:47:10  INFO      httpx  │  HTTP Request: POST https://green-surface.f3next.in/api/resource/BOM "HTTP/1.1 200 OK"
16:47:10  INFO      shared.erp_adapters.erpnext  │  ERPNextAdapter.get_doctype_schema: fetching live schema for BOM
16:47:11  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/DocType/BOM "HTTP/1.1 200 OK"
16:47:11  INFO      shared.erp_adapters.erpnext  │  ERPNextAdapter.get_doctype_schema: BOM → 50 fields
16:47:11  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/BOM?fields=%5B%22name%22%5D&limit_page_length=1&limit_start=0&filters=%5B%5B%22name%22%2C+%22%3D%22%2C+%22FG-PRIMER-B%22%5D%5D "HTTP/1.1 200 OK"
16:47:11  INFO      httpx  │  HTTP Request: POST https://green-surface.f3next.in/api/resource/BOM "HTTP/1.1 200 OK"
16:47:13  INFO      is_harness.activity  │  ✅ execute_import_phase done | phase=phase_b_master records=8
16:47:13  INFO      is_harness  │
16:47:13  INFO      is_harness  │  ════════════════════════════════════════════════════════════════════════
16:47:13  INFO      is_harness  │    ✅  STEP COMPLETE: execute_import_phase
16:47:13  INFO      is_harness  │  ════════════════════════════════════════════════════════════════════════
16:47:13  INFO      is_harness  │

{
  "phase": "phase_b_master",
  "status": "success",
  "steps_completed": 2,
  "steps_failed": 0,
  "records_created": 8,
  "execution_logs": [
    {
      "step": 1,
      "doctype": "Item",
      "status": "success",
      "records_attempted": 6,
      "records_succeeded": 6,
      "records_failed": 0,
      "duration_seconds": 5,
      "resolution_summary": {
        "resolved_count": 0,
        "corrections": [],
        "unresolvable_values": [],
        "ambiguous": {},
        "doctype": "Item"
      }
    },
    {
      "step": 3,
      "doctype": "BOM",
      "status": "success",
      "records_attempted": 2,
      "records_succeeded": 2,
      "records_failed": 0,
      "duration_seconds": 2,
      "resolution_summary": {
        "resolved_count": 0,
        "corrections": [],
        "unresolvable_values": [],
        "ambiguous": {},
        "doctype": "BOM"
      }
    }
  ]
}

PS C:\dev\F3Next> ^C
PS C:\dev\F3Next> python -m containers.implementation.is_harness --step preflight_import --phase phase_b_master
21:54:05  INFO      is_harness  │
21:54:05  INFO      is_harness  │  ════════════════════════════════════════════════════════════════════════
21:54:05  INFO      is_harness  │    IS STEP HARNESS
21:54:05  INFO      is_harness  │    step     : preflight_import
21:54:05  INFO      is_harness  │    mock_llm : False
21:54:05  INFO      is_harness  │    dry_run  : False
21:54:05  INFO      is_harness  │  ════════════════════════════════════════════════════════════════════════
21:54:05  INFO      is_harness  │
21:54:06  INFO      is_harness  │    Fixture  : C:\dev\F3Next\containers\implementation\dev_fixtures\preflight_import.json
21:54:06  INFO      is_harness  │    Input    : {"_comment": "Read-only preflight for an import phase. No ERPNext writes.", "session_id": "8a1d1297-39d3-4b88-82a3-cbca4983218b", "phase_id": "phase_c_transactional", "project_id": "b6ff0b7f-a616-4179...
21:54:06  INFO      is_harness  │
21:54:07  INFO      is_harness.activity  │  ▶ preflight_import started | session=8a1d1297-39d3-4b88-82a3-cbca4983218b phase=phase_b_master
21:54:12  INFO      is_harness.activity  │    🔑 Auto-resolved base_url from Project.deployment_details: https://green-surface.f3next.in
21:54:12  INFO      is_harness.activity  │    🔑 Auto-resolved API credentials from Project.deployment_details
21:54:16  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Item?fields=%5B%22name%22%2C+%22disabled%22%5D&limit_page_length=1000&limit_start=0&filters=%5B%5B%22disabled%22%2C+%22%3D%22%2C+0%5D%5D "HTTP/1.1 200 OK"
21:54:16  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Item%20Group?fields=%5B%22name%22%5D&limit_page_length=1000&limit_start=0 "HTTP/1.1 200 OK"
21:54:17  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/UOM?fields=%5B%22name%22%5D&limit_page_length=1000&limit_start=0 "HTTP/1.1 200 OK"
21:54:17  INFO      is_harness.activity  │  ✅ preflight_import done | phase=phase_b_master requires_gate=False
21:54:17  INFO      is_harness  │
21:54:17  INFO      is_harness  │  ════════════════════════════════════════════════════════════════════════
21:54:17  INFO      is_harness  │    ✅  STEP COMPLETE: preflight_import
21:54:17  INFO      is_harness  │  ════════════════════════════════════════════════════════════════════════
21:54:17  INFO      is_harness  │

{
  "phase_id": "phase_b_master",
  "status": "ready",
  "blockers": [
    "1 data gap(s) in plan"
  ],
  "data_gaps": [
    {
      "doctype": "Supplier",
      "step": 7
    }
  ],
  "link_corrections": [],
  "unresolvable_links": [],
  "draft_parents": [],
  "confirmation_preview": {
    "phase_id": "phase_b_master",
    "requires_confirmation": false,
    "total_records": 9,
    "create_steps": [
      {
        "doctype": "Item",
        "records": 6,
        "risk_tier": "low"
      },
      {
        "doctype": "BOM",
        "records": 3,
        "risk_tier": "medium"
      }
    ],
    "high_risk_doctypes": [],
    "medium_risk_doctypes": [
      "BOM"
    ],
    "draft_parents": [],
    "link_corrections": [],
    "warnings": [],
    "message": "About to import: 6 Item, 3 BOM."
  },
  "requires_confirmation": false,
  "requires_execution_gate": false
}

PS C:\dev\F3Next> python -m containers.implementation.is_harness --step preflight_import --phase phase_c_transactional
21:54:20  INFO      is_harness  │
21:54:20  INFO      is_harness  │  ════════════════════════════════════════════════════════════════════════
21:54:20  INFO      is_harness  │    IS STEP HARNESS
21:54:20  INFO      is_harness  │    step     : preflight_import
21:54:20  INFO      is_harness  │    mock_llm : False
21:54:20  INFO      is_harness  │    dry_run  : False
21:54:20  INFO      is_harness  │  ════════════════════════════════════════════════════════════════════════
21:54:20  INFO      is_harness  │
21:54:21  INFO      is_harness  │    Fixture  : C:\dev\F3Next\containers\implementation\dev_fixtures\preflight_import.json
21:54:21  INFO      is_harness  │    Input    : {"_comment": "Read-only preflight for an import phase. No ERPNext writes.", "session_id": "8a1d1297-39d3-4b88-82a3-cbca4983218b", "phase_id": "phase_c_transactional", "project_id": "b6ff0b7f-a616-4179...
21:54:21  INFO      is_harness  │
21:54:22  INFO      is_harness.activity  │  ▶ preflight_import started | session=8a1d1297-39d3-4b88-82a3-cbca4983218b phase=phase_c_transactional
21:54:27  INFO      is_harness.activity  │    🔑 Auto-resolved base_url from Project.deployment_details: https://green-surface.f3next.in
21:54:27  INFO      is_harness.activity  │    🔑 Auto-resolved API credentials from Project.deployment_details
21:54:29  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Item?fields=%5B%22name%22%2C+%22disabled%22%5D&limit_page_length=1000&limit_start=0&filters=%5B%5B%22disabled%22%2C+%22%3D%22%2C+0%5D%5D "HTTP/1.1 200 OK"
21:54:29  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/BOM?fields=%5B%22name%22%5D&limit_page_length=1000&limit_start=0 "HTTP/1.1 200 OK"
21:54:29  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/Warehouse?fields=%5B%22name%22%2C+%22disabled%22%5D&limit_page_length=1000&limit_start=0&filters=%5B%5B%22disabled%22%2C+%22%3D%22%2C+0%5D%5D "HTTP/1.1 200 OK"
21:54:29  INFO      is_harness.activity  │  BulkLinkResolver: Warehouse 'WIP - Factory' -> 'Work In Progress - GS'
21:54:30  INFO      httpx  │  HTTP Request: GET https://green-surface.f3next.in/api/resource/BOM?fields=%5B%22name%22%2C+%22docstatus%22%2C+%22item%22%5D&limit_page_length=50&limit_start=0&filters=%5B%5B%22docstatus%22%2C+%22%3D%22%2C+0%5D%5D "HTTP/1.1 200 OK"
21:54:30  INFO      is_harness.activity  │  ✅ preflight_import done | phase=phase_c_transactional requires_gate=True
21:54:30  INFO      is_harness  │
21:54:30  INFO      is_harness  │  ════════════════════════════════════════════════════════════════════════
21:54:30  INFO      is_harness  │    ✅  STEP COMPLETE: preflight_import
21:54:30  INFO      is_harness  │  ════════════════════════════════════════════════════════════════════════
21:54:30  INFO      is_harness  │

{
  "phase_id": "phase_c_transactional",
  "status": "ready",
  "blockers": [
    "2 data gap(s) in plan"
  ],
  "data_gaps": [
    {
      "doctype": "Stock Entry",
      "step": 9
    },
    {
      "doctype": "Purchase Receipt",
      "step": 10
    }
  ],
  "link_corrections": [
    {
      "field": "wip_warehouse",
      "target_doctype": "Warehouse",
      "original": "WIP - Factory",
      "corrected": "Work In Progress - GS"
    },
    {
      "field": "wip_warehouse",
      "target_doctype": "Warehouse",
      "original": "WIP - Factory",
      "corrected": "Work In Progress - GS"
    }
  ],
  "unresolvable_links": [],
  "draft_parents": [
    {
      "doctype": "BOM",
      "name": "BOM-FG-PRIMER-A-002",
      "docstatus": 0,
      "blocks": [
        "Work Order"
      ]
    },
    {
      "doctype": "BOM",
      "name": "BOM-FG-PRIMER-B-002",
      "docstatus": 0,
      "blocks": [
        "Work Order"
      ]
    }
  ],
  "confirmation_preview": {
    "phase_id": "phase_c_transactional",
    "requires_confirmation": true,
    "total_records": 2,
    "create_steps": [
      {
        "doctype": "Work Order",
        "records": 2,
        "risk_tier": "medium"
      }
    ],
    "high_risk_doctypes": [],
    "medium_risk_doctypes": [
      "Work Order"
    ],
    "draft_parents": [
      {
        "doctype": "BOM",
        "name": "BOM-FG-PRIMER-A-002",
        "docstatus": 0,
        "blocks": [
          "Work Order"
        ]
      },
      {
        "doctype": "BOM",
        "name": "BOM-FG-PRIMER-B-002",
        "docstatus": 0,
        "blocks": [
          "Work Order"
        ]
      }
    ],
    "link_corrections": [
      {
        "field": "wip_warehouse",
        "target_doctype": "Warehouse",
        "original": "WIP - Factory",
        "corrected": "Work In Progress - GS"
      },
      {
        "field": "wip_warehouse",
        "target_doctype": "Warehouse",
        "original": "WIP - Factory",
        "corrected": "Work In Progress - GS"
      }
    ],
    "warnings": [
      "Draft BOM 'BOM-FG-PRIMER-A-002' may block Work Order",
      "Draft BOM 'BOM-FG-PRIMER-B-002' may block Work Order"
    ],
    "message": "About to import: 2 Work Order. Draft parent documents detected (BOM BOM-FG-PRIMER-A-002, BOM BOM-FG-PRIMER-B-002) \u2014 submit or confirm to proceed."
  },
  "requires_confirmation": true,
  "requires_execution_gate": true
}

PS C:\dev\F3Next> python -m containers.implementation.is_harness --step execute_import_phase --phase phase_b_master --confirm-execution
21:56:23  INFO      is_harness  │
21:56:23  INFO      is_harness  │  ════════════════════════════════════════════════════════════════════════
21:56:23  INFO      is_harness  │    IS STEP HARNESS
21:56:23  INFO      is_harness  │    step     : execute_import_phase
21:56:23  INFO      is_harness  │    mock_llm : False
21:56:23  INFO      is_harness  │    dry_run  : False
21:56:23  INFO      is_harness  │  ════════════════════════════════════════════════════════════════════════
21:56:23  INFO      is_harness  │
21:56:24  INFO      is_harness  │    Fixture  : C:\dev\F3Next\containers\implementation\dev_fixtures\execute_import_phase.json
21:56:24  INFO      is_harness  │    Input    : {"_comment": "Executes one import phase against ERPNext. Use --dry-run to skip actual API writes. Requires build_import_plan to have run first for this session.", "session_id": "8a1d1297-39d3-4b88-82a...
21:56:24  INFO      is_harness  │
21:56:25  INFO      is_harness.activity  │  ▶ execute_import_phase started | session=8a1d1297-39d3-4b88-82a3-cbca4983218b phase=phase_b_master dry_run=True
21:56:30  INFO      is_harness.activity  │    🔑 Auto-resolved base_url from Project.deployment_details: https://green-surface.f3next.in
21:56:30  INFO      is_harness.activity  │    🔑 Auto-resolved API credentials from Project.deployment_details
21:56:31  INFO      is_harness.activity  │
21:56:31  INFO      is_harness.activity  │
21:56:33  WARNING   is_harness.activity  │    ⚠️  DATA GAP: Supplier has no mapped data file and no baseline — skipping
21:56:36  INFO      is_harness.activity  │  ✅ execute_import_phase done | phase=phase_b_master records=8
21:56:36  INFO      is_harness  │
21:56:36  INFO      is_harness  │  ════════════════════════════════════════════════════════════════════════
21:56:36  INFO      is_harness  │    ✅  STEP COMPLETE: execute_import_phase
21:56:36  INFO      is_harness  │  ════════════════════════════════════════════════════════════════════════
21:56:36  INFO      is_harness  │

{
  "phase": "phase_b_master",
  "status": "success",
  "steps_completed": 2,
  "steps_failed": 0,
  "records_created": 8,
  "execution_logs": [
    {
      "step": 1,
      "doctype": "Item",
      "status": "success",
      "records_attempted": 6,
      "records_succeeded": 6,
      "records_failed": 0,
      "duration_seconds": 1,
      "resolution_summary": {},
      "submit_summary": {
        "submitted_count": 0,
        "actions": []
      }
    },
    {
      "step": 3,
      "doctype": "BOM",
      "status": "success",
      "records_attempted": 2,
      "records_succeeded": 2,
      "records_failed": 0,
      "duration_seconds": 0,
      "resolution_summary": {},
      "submit_summary": {
        "submitted_count": 0,
        "actions": []
      }
    }
  ]
}

PS C:\dev\F3Next> python -m containers.implementation.is_harness --step execute_import_phase --phase phase_c_transactional --confirm-execution
21:57:50  INFO      is_harness  │
21:57:50  INFO      is_harness  │  ════════════════════════════════════════════════════════════════════════
21:57:50  INFO      is_harness  │    IS STEP HARNESS
21:57:50  INFO      is_harness  │    step     : execute_import_phase
21:57:50  INFO      is_harness  │    mock_llm : False
21:57:50  INFO      is_harness  │    dry_run  : False
21:57:50  INFO      is_harness  │  ════════════════════════════════════════════════════════════════════════
21:57:50  INFO      is_harness  │
21:57:51  INFO      is_harness  │    Fixture  : C:\dev\F3Next\containers\implementation\dev_fixtures\execute_import_phase.json
21:57:51  INFO      is_harness  │    Input    : {"_comment": "Executes one import phase against ERPNext. Use --dry-run to skip actual API writes. Requires build_import_plan to have run first for this session.", "session_id": "8a1d1297-39d3-4b88-82a...
21:57:51  INFO      is_harness  │
21:57:52  INFO      is_harness.activity  │  ▶ execute_import_phase started | session=8a1d1297-39d3-4b88-82a3-cbca4983218b phase=phase_c_transactional dry_run=True
21:57:58  INFO      is_harness.activity  │    🔑 Auto-resolved base_url from Project.deployment_details: https://green-surface.f3next.in
21:57:58  INFO      is_harness.activity  │    🔑 Auto-resolved API credentials from Project.deployment_details
21:57:59  INFO      is_harness.activity  │
21:57:59  INFO      is_harness.activity  │
21:57:59  WARNING   is_harness.activity  │    ⚠️  DATA GAP: Stock Entry has no mapped data file and no baseline — skipping
21:57:59  WARNING   is_harness.activity  │    ⚠️  DATA GAP: Purchase Receipt has no mapped data file and no baseline — skipping
21:58:04  INFO      is_harness.activity  │  ✅ execute_import_phase done | phase=phase_c_transactional records=2
21:58:04  INFO      is_harness  │
21:58:04  INFO      is_harness  │  ════════════════════════════════════════════════════════════════════════
21:58:04  INFO      is_harness  │    ✅  STEP COMPLETE: execute_import_phase
21:58:04  INFO      is_harness  │  ════════════════════════════════════════════════════════════════════════
21:58:04  INFO      is_harness  │

{
  "phase": "phase_c_transactional",
  "status": "success",
  "steps_completed": 1,
  "steps_failed": 0,
  "records_created": 2,
  "execution_logs": [
    {
      "step": 3,
      "doctype": "Work Order",
      "status": "success",
      "records_attempted": 2,
      "records_succeeded": 2,
      "records_failed": 0,
      "duration_seconds": 1,
      "resolution_summary": {},
      "submit_summary": {
        "submitted_count": 0,
        "actions": []
      }
    }
  ]
}

PS C:\dev\F3Next> python -m containers.os.action_harness --intent "list open work orders" --project-id b6ff0b7f-a616-4179-8f68-deda9b3578af --preview-only
21:58:45  INFO      containers.os.clarity_agent.kb_loader  │  Loading ERP-OS Knowledge Base...
21:58:45  INFO      containers.os.clarity_agent.kb_loader  │  KB loaded: 23 intents, 111 synonyms, 17 abbreviations
21:58:53  INFO      httpx  │  HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
21:58:53  INFO      shared.llm_providers.openai_provider  │  [OpenAIProvider] Tool call: search_cvs_master_data({'query': 'open work orders', 'entity_type': 'Item'})
21:58:56  INFO      containers.os.clarity_agent.activities  │  CVS Tool: query='open work orders' entity=Item tokens=['open', 'work', 'orders'] → 0 matches
21:58:56  INFO      shared.llm_providers.openai_provider  │  [OpenAIProvider] Tool 'search_cvs_master_data' returned 0 result(s)
21:59:05  INFO      httpx  │  HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
21:59:12  INFO      httpx  │  HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
21:59:12  INFO      action_harness  │  extract_intent: intent=search_documents  doctype=Work Order  confidence=0.95  ambiguities=0
21:59:12  INFO      containers.os.command_planner.kb_plans  │  Command Planner: loading knowledge base...
21:59:12  INFO      containers.os.command_planner.kb_plans  │  Plan KB loaded: 10 patterns, 33 trigger keywords, 23 intent metas
21:59:12  INFO      containers.os.command_planner.plan_builder  │  Planner: single-step plan for intent 'search_documents'
21:59:12  INFO      containers.os.command_planner.prereq_resolver  │  Planner prereq resolution skipped — ERP credentials unavailable
21:59:12  INFO      containers.os.command_planner.activities  │  plan_command: intent=search_documents → pattern=single-step steps=1 prereqs=0 risk=none confirm=False
21:59:12  INFO      containers.os.command_planner.activities  │  plan_command detail:
{
  "plan_id": "a435a0c4-f012-4b73-aa7a-9c4897099e54",
  "pattern_id": null,
  "pattern_name": null,
  "steps": [
    {
      "step_number": 1,
      "action": "search",
      "doctype": "Any",
      "depends_on": null,
      "rollback_if_failed": false,
      "source_doctype": null,
      "source_step": null,
      "fetch_fields": [],
      "required_fields": [
        "doctype"
      ],
      "optional_fields": [
        "filters"
      ],
      "entities": {
        "items": [],
        "transaction_date": "2026-05-24"
      },
      "description": "Search Any",
      "rollback_note": "",
      "step_role": "main",
      "prerequisite_for": null,
      "resolution_source": null,
      "payload_template": {}
    }
  ],
  "risk_level": "none",
  "requires_confirmation": false,
  "confirmation_message": null,
  "estimated_api_calls": 1,
  "is_multi_step": false,
  "is_async": false,
  "rollback_strategy": "none",
  "success_message_template": null,
  "partial_failure_template": null
}
21:59:12  INFO      containers.os.payload_generator.kb_fields  │  Field KB loaded: 13 doctypes in KB-04
21:59:12  INFO      containers.os.payload_generator.payload_builder  │  Payload bundle: 1 step(s) for intent=search_documents doctype=Work Order  company=
21:59:12  INFO      containers.os.payload_generator.payload_builder  │    step 1 [main]: search Any  (3 payload keys)
21:59:12  INFO      action_harness  │  generate_payload: intent=search_documents doctype=Work Order steps=1
21:59:12  INFO      action_harness  │    step 1 [main]: search Any → POST   (3 payload keys)
21:59:12  INFO      action_harness  │  Preview only — no ERPNext writes. Use --confirm to execute.
{
  "status": "preview",
  "intent": {
    "intent_id": "search_documents",
    "category": "search",
    "target_doctype": "Work Order",
    "action": "list",
    "erp_type": "erpnext",
    "entities": {
      "item_code": null,
      "customer": null,
      "supplier": null,
      "items": [],
      "transaction_date": "2026-05-24",
      "delivery_date": null,
      "amount": null,
      "currency": null,
      "payment_type": null,
      "mode_of_payment": null,
      "from_warehouse": null,
      "to_warehouse": null,
      "stock_entry_type": null,
      "company": null,
      "extra": {},
      "due_date": null,
      "posting_date": null,
      "po_no": null,
      "so_no": null,
      "dn_no": null,
      "invoice_no": null,
      "payment_reference": null,
      "party_type": null,
      "project": null,
      "price_list": null
    },
    "confidence": 0.95,
    "ambiguities": [],
    "has_ambiguities": false,
    "risk_level": "low",
    "requires_confirmation": false,
    "raw_prompt": "list open work orders",
    "session_context": []
  },
  "plan": {
    "plan_id": "a435a0c4-f012-4b73-aa7a-9c4897099e54",
    "pattern_id": null,
    "pattern_name": null,
    "steps": [
      {
        "step_number": 1,
        "action": "search",
        "doctype": "Any",
        "depends_on": null,
        "rollback_if_failed": false,
        "source_doctype": null,
        "source_step": null,
        "fetch_fields": [],
        "required_fields": [
          "doctype"
        ],
        "optional_fields": [
          "filters"
        ],
        "entities": {
          "items": [],
          "transaction_date": "2026-05-24"
        },
        "description": "Search Any",
        "rollback_note": "",
        "step_role": "main",
        "prerequisite_for": null,
        "resolution_source": null,
        "payload_template": {}
      }
    ],
    "risk_level": "none",
    "requires_confirmation": false,
    "confirmation_message": null,
    "estimated_api_calls": 1,
    "is_multi_step": false,
    "is_async": false,
    "rollback_strategy": "none",
    "success_message_template": null,
    "partial_failure_template": null
  },
  "payload_preview": {
    "steps": [
      {
        "step_number": 1,
        "action": "search",
        "doctype": "Any",
        "payload": {
          "filters": [],
          "limit": 20,
          "fields": [
            "name",
            "status"
          ]
        },
        "notes": "Search Any"
      }
    ]
  },
  "confirmation_preview": {
    "intent_id": "search_documents",
    "target_doctype": "Work Order",
    "action": "list",
    "requires_confirmation": false,
    "high_risk_doctypes": [],
    "warnings": [],
    "plan_steps": 1,
    "payload_steps": 1,
    "message": "About to list Work Order (1 step(s)).",
    "create_steps": [
      {
        "doctype": "Any",
        "action": "search",
        "records": 1,
        "risk_tier": "low"
      }
    ]
  }
}
PS C:\dev\F3Next>




##### just tell me if the IS and our product is ready for any company now or not yet !
atleast green-surface - but i dont want our product to be hardcoded for green-surface, is it like atleast 90-95% ready to use for companies, if KB added ??



---

**Cursor**

Short answer: **not ready for “any company” yet**. For **Green Surface specifically**, you’re roughly **70–80% there on the import path**, not 90–95%. With a **full KB + more product work**, you could get toward **85–90% for similar manufacturing SMEs on ERPNext** — but that’s not the same as “any company.”

---

## What your runs actually show

### Preflight — working as designed
- **Phase B:** `requires_execution_gate: false`, Supplier data gap flagged (expected).
- **Phase C:** Link fix preview works (`WIP - Factory` → `Work In Progress - GS`), gate fires because **draft BOMs** `BOM-FG-PRIMER-A-002` / `-B-002` would block Work Orders.

That preflight output is good product behavior — it’s catching real state before writes.

### Live import runs — did NOT actually hit ERPNext
Both runs with `--confirm-execution` logged:

```text
dry_run=True
```

Your fixture [`execute_import_phase.json`](containers/implementation/dev_fixtures/execute_import_phase.json) has `"dry_run": true`.  
`--confirm-execution` only bypasses the **execution gate**; it does **not** turn off dry run.

So:
- No `Pass 2.6: submitted BOM` (submit never runs in dry run)
- `submit_summary.submitted_count: 0` — expected in dry run, not proof auto-submit failed
- Phase C “success” with 2 records = **mock success**, not new Work Orders in ERPNext

Your **16:46 Phase B run** (before `--confirm-execution`) *did* write live — and created duplicate draft BOMs (`-002`), which is why preflight now warns about drafts.

---

## Is the product hardcoded to Green Surface?

**No at the product level**, but **yes in a few dev shortcuts**:

| Hardcoded? | What |
|---|---|
| Dev fixtures only | Session `8a1d1297`, project `b6ff0b7f`, `green-surface` slug |
| Code shortcuts | WIP/FG warehouse aliases (manufacturing/ERPNext naming pattern) |
| Architecture | ERPNext-only adapter, ERPNext doctype graph, frappe submit API |
| Not hardcoded | Pipeline shape, F3ICHE/industry playbooks, mapping, phases, preflight/gate logic |

Green Surface is your **test tenant**, not baked into core logic — except those warehouse aliases and ERPNext-specific lifecycle rules.

---

## Readiness by scope

### Green Surface (manufacturing, this session’s mapped data)

| Area | Ready? | Notes |
|---|---|---|
| Phase A seeds | Yes | Idempotent |
| Phase B Items | Yes | Skips existing |
| Phase B BOM + auto-submit | **Not verified live** | Re-run with real writes |
| Phase C Work Orders + link resolve | **Was proven earlier** (manual BOM submit) | Not re-proven after Pass 2.6 |
| Preflight / execution gate | Yes | Phase C gate correctly warns on draft BOMs |
| Supplier / Stock Entry / PR | No | Data gaps — need uploads |
| Clean ERPNext state | No | Extra draft BOMs `-002` from old runs |

**Green Surface: ~70–80%** on the import slice you’ve mapped — **not “done”** until one clean live B→C run with auto-submit and no draft-parent warnings.

### “Any company” (different industry, different ERP, different data shape)

| Requirement | Status |
|---|---|
| Upload + map arbitrary files | Partial — quality varies a lot |
| ERP other than ERPNext | No — only `erpnext` in registry |
| Trading / services / retail (no BOM/WO) | Partial — less tested |
| Financial docs (SI, payments) | Fragile — high-risk gates exist, not fully tested |
| Full 14-step workflow + UI gates | Partial — harness proves activities, not full UX |
| KB-only config (no code) | **Not yet** — lifecycle still has `_BUILTIN_LIFECYCLE`, warehouse aliases in code |

**Any company today: ~40–50%** as a product.  
**Similar ERPNext manufacturing SME with good KB/playbooks: ~75–85%** after you finish lifecycle testing and clean up hardcoded bits.

**90–95% with “KB added” alone:** **No.** KB helps a lot for doctype order, lifecycle, risk tiers, playbooks — but you still need:
- Live verification of Pass 2.6
- BOM dedup working on re-run (item+company check)
- More doctypes / industries tested
- Upload gaps handled in UI
- Optional: move aliases + lifecycle fully into KB
- Second ERP adapter if “any ERP” is the bar

---

## One command fix before you judge Pass 2.6

For a **real** live test, either set fixture `"dry_run": false` or add harness support to force live (today `--confirm-execution` is not enough):

```powershell
# Option: temporarily set dry_run false in execute_import_phase.json, then:
python -m containers.implementation.is_harness --step execute_import_phase --phase phase_b_master --confirm-execution
```

Success looks like logs with `Pass 2.6: submitted BOM '...'` and `submit_summary.submitted_count > 0`, then Phase C preflight with **no draft BOM warnings** (or only the submitted `-001` BOMs).

---

## Bottom line

| Question | Answer |
|---|---|
| Ready for any company now? | **No** |
| Ready for Green Surface end-to-end without manual steps? | **Almost — not proven on latest code in live mode** |
| Hardcoded to Green Surface? | **Fixtures/dev yes; core product mostly no; ERPNext/manufacturing bias yes** |
| 90–95% ready if KB added? | **No — KB gets you toward ~85% for similar ERPNext SMEs, not universal readiness** |

**Product honest stage:** Strong **ERPNext onboarding prototype** with real Green Surface wins (link resolve, preflight, gates, OS preview harness). Not yet a **general-purpose, any-company IS** until you live-verify lifecycle, clean duplicate BOM state, broaden tested industries, and push more rules into KB instead of code.

If you want, switch to Agent mode and we can fix the harness so `--confirm-execution` implies live writes (or add `--live`), then run the real B→C proof on Green Surface.

