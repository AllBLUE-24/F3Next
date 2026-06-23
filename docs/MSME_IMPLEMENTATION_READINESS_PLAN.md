# MSME Implementation Readiness Plan

> **Purpose:** CEO/CTO product plan for the “last mile” after mapping — value translation, site bootstrap, and MSME-trust UX.  
> **Last updated:** 2026-06-23  
> **Evidence:** Green Surface `4th_run` golden run — validation report + mapped payloads in `attachments/green-surface/greensurface_golden_data/4th_run/Z_output.json`  
> **Related:** [`FOUNDATIONS.md`](./FOUNDATIONS.md) · [`PRIORITIES.md`](./PRIORITIES.md) · [`STRUCTURAL_FIXES_4TH_RUN.md`](./STRUCTURAL_FIXES_4TH_RUN.md) · [`ARCH_KNOWLEDGE_BASE.md`](./ARCH_KNOWLEDGE_BASE.md) · [`GOLDEN_MATRIX_MANIFEST.md`](./GOLDEN_MATRIX_MANIFEST.md)

---

## Executive summary

Mapping for the 4th_run corpus **works** (6/6 files, party split, UOM normalization). The run fails at **Step 11 validation** because two **cell values** from Tally exports do not exist as link targets on the live ERPNext site:

- `item_group: "Raw Materials"` (3 items)
- `customer_group: "Sundry Debtors"` (2 customers — a Tally **ledger class**, not an ERPNext Customer Group)

We are **not** fixing this by exploding column synonyms. We are adding two new capabilities:

1. **Value Translation Layer (VTL)** — maps *cell values* (Tally/Excel → ERPNext/f3iche/live site), separate from header/column mapping.
2. **Site Config Bootstrap (SCB)** — scans the live site, derives missing config masters from mapped payloads, and creates or maps them before validation hard-blocks.

Together with an honest supervisor UX, this is what makes F3Next usable for MSMEs who upload messy Tally/Excel exports without an ERP consultant in the room.

---

## New KB / platform layers (what we are bringing in)

Today’s KB stack (see [`ARCH_KNOWLEDGE_BASE.md`](./ARCH_KNOWLEDGE_BASE.md)) stops at **column/header synonyms** and **empty-field defaults**. That is not enough for MSME exports.

| Layer | Name | Owns | Example |
| ----- | ---- | ---- | ------- |
| **Existing L3** | Schema / column KB | Header → ERPNext fieldname | `Name_of_Item` → `item_code` |
| **New: VTL** | **Value Translation Layer** | Cell value → ERPNext value or policy | `Raw Materials` → `Raw Material`; `Sundry Debtors` → *(drop; use default)* |
| **New: SCB** | **Site Config Bootstrap** | Live ERP scan + derive/create config masters | Create `Raw Material` Item Group on site before Item import |
| **Existing L1** | Honesty contracts | Supervisor actions must actually fix or explain | `Continue with defaults` → real `auto_fix`, not no-op |

**VTL sources (priority order):**

1. Live ERP fuzzy match (uses *their* site names — best for MSME)
2. f3iche defaults (`default_item_group`, industry norms)
3. **Source-system packs** — small curated maps per legacy system (Tally, Busy, Zoho), not per-company KB bloat
4. LLM propose once → user confirm → promote to session memory → optional KB promotion path

**SCB scope (Phase 1):**

- Item Group, Customer Group, Supplier Group, Territory, UOM (when not already covered by LER)
- Derive distinct values from mapped payloads in the current session
- Queue as **Phase 0 config import** before master/transactional phases

**Foundation placement:**

- VTL → extends **L3 ERP Knowledge** (new modular files under `schema/value_translation/`)
- SCB → new activity between mapping confirmation and validation (**L2 corpus spine** + **L4 import ordering**)
- Supervisor honesty → **L1** + **L5 Observability UX**

---

## Overview table — issue, fix, MSME empathy

| # | Issue (what breaks) | Fix (what we ship) | What the MSME feels / wants |
| - | ------------------- | ------------------ | --------------------------- |
| **1** | Tally `Under_Group` lands on `customer_group` as `Sundry Debtors` — not an ERPNext group | **Party-field semantics:** use `Under_Group` only for Customer/Supplier **split**; never map ledger class to `customer_group` / `supplier_group`; apply f3iche/baseline defaults instead | *“I didn’t mean create a Tally group in ERP — I just exported my customer list.”* |
| **2** | `item_group: "Raw Materials"` not on live site; validation blocks | **VTL + SCB:** fuzzy map to existing group OR derive Item Group rows from payload OR replace with f3iche default | *“My stock list says Raw Materials — just set it up like a normal factory.”* |
| **3** | “Continue with defaults” sends signal but applies **no** payload change; same 5 errors loop | **Supervisor auto_fix:** `continue_with_defaults` triggers `map_enum` / VTL / KB defaults on **populated** invalid links, then re-validates | *“When I click Continue, something should actually happen.”* |
| **4** | Supervisor card says “Customer Group, Item Group” without values or actions | **Unified gap cards:** show field, value, row count, live ERP dropdown, one-click map | *“Tell me exactly what’s wrong in one sentence I understand.”* |
| **5** | Banner + right panel + chat = three surfaces; note field doesn’t fix anything | **One assistant surface:** chat and buttons share backend; banner is slim pointer only | *“One place to talk to the system, not three red boxes.”* |
| **6** | Greenfield deferral works for Item/Customer/Project masters but not config links | **Extend greenfield policy:** defer or bootstrap Item Group / Customer Group when session will create them in Phase 0 | *“You’re already creating my items — why stop for a group name?”* |
| **7** | Column mapping still needs tier-0/KB for Tally headers | **Keep tier-0 + modular KB** for headers; **don’t** duplicate as value synonyms | *“My file looks like Tally — the system should recognize that.”* |
| **8** | Partial upload (3 files, then 3 more) works but feels accidental | **Upload wave UX:** celebrate round 2, show file union, readiness delta | *“I can add files later without starting over.”* |
| **9** | `ler_gaps` hints (“will be created on import”) hidden in JSON | **Import preview checklist:** masters vs transactions vs config to be created | *“What will happen to my data before I click Import?”* |
| **10** | No release gate for 4th_run validate pass after mapping | **Golden matrix row:** 4th_run → validate pass → import pass in CI | *“This product works for companies like mine.”* (implementer/partner trust) |

---

## Detailed plan

### 1. Value Translation Layer (VTL) — new KB module

**Problem**

Column mapping answers: *which CSV column is `item_group`?*  
Validation answers: *does the value `"Raw Materials"` exist on the site?*  
There is no layer that answers: *what should `"Raw Materials"` become on this ERPNext site?*

From `Z_output.json`, Items are mapped correctly — the failure is **value**, not header:

```json
"item_group": "Raw Materials"
"customer_group": "Sundry Debtors"
```

**Design**

Add modular KB under `containers/knowledge_base/erpnext/schema/value_translation/`:

```
value_translation/
├── index.json                 # compose loader (mirrors mapping/index.json)
├── tally.json                 # ledger/group vocabulary → policy
├── erpnext_baseline.json      # singular/plural, common aliases
└── link_field_policies.json   # fields that accept remap vs must exist on site
```

**Policies (examples)**

| Source | Raw value | Policy | Target |
| ------ | --------- | ------ | ------ |
| Tally | `Sundry Debtors` | `drop_use_default` | `customer_group` → f3iche or `All Customer Groups` |
| Tally | `Sundry Creditors` | `drop_use_default` | `supplier_group` → `All Supplier Groups` |
| Tally/Excel | `Raw Materials` | `fuzzy_live_erp` then `map` | `Raw Material` or site-specific name |
| Tally/Excel | `Finished Goods` | `fuzzy_live_erp` | match existing FG group on site |
| UOM | `Ltr` | `kb_alias` | `Litre` *(already in parsing_defaults — VTL unifies this pattern)* |

**Runtime hook**

- Run VTL in `apply_defaults_and_normalize()` **after** column map, **before** preflight/validation
- Also run in supervisor `auto_fix` when user chooses “Continue with defaults”
- Log every translation with `{field, from, to, rule_id}` for Validate UI transparency

**Why not a huge synonym list**

Source-system **packs** (Tally ~50 rules) plus live ERP fuzzy match scale to many MSMEs without per-company KB maintenance. LLM fills gaps once; promotion path moves repeats into pack or session memory.

---

### 2. Site Config Bootstrap (SCB) — new pipeline step

**Problem**

LER checks link fields against **live ERP now**. Item and Customer masters can be deferred (greenfield), but Item Group and Customer Group are config masters — validation treats them as hard blockers even when the import plan would create Items/Customers in the same session.

**Design**

New activity: `bootstrap_site_config` (Step **10b**, after mapping confirmation, before or integrated with validation):

1. **Scan** live ERP: Item Groups, Customer Groups, Supplier Groups, Territories, UOMs (reuse BulkLinkResolver fetch cache)
2. **Collect** distinct link values from all mapped payloads in session
3. For each missing config value:
   - Apply VTL (fuzzy map to existing)
   - If still missing: emit **derived config records** (e.g. Item Group rows) into R2 `mappings/mapped_payloads/Item Group.json`
   - Insert into import plan **Phase 0 — Site config** before Item/Customer masters
4. Re-run LER; blocking count should drop to zero for greenfield sites

**Greenfield policy extension**

Extend `ler_greenfield.py` or parallel policy in `classify_ler_unresolvable`:

- If `link_target` in `{Item Group, Customer Group, Supplier Group}` **and** session has derived bootstrap rows for that value → disposition `info` (“will be created in config phase”) instead of `blocking`

**MSME empathy**

MSMEs never say “upload Item Group CSV.” They say “set up my company.” SCB should default to **auto-bootstrap with preview**, not another upload gate.

---

### 3. Party-field semantics fix (P0 bug)

**Problem**

On `tally_sundry_ledgers.csv`, `Under_Group` correctly drives **party split** (`Sundry Debtors` → Customer, `Sundry Creditors` → Supplier). It must **not** also map to `customer_group` / `supplier_group` on mapped rows.

Tally ledger classification ≠ ERPNext commercial grouping.

**Fix**

- In party-split mapping path: exclude `Under_Group` from field mapping to `customer_group` / `supplier_group` / `item_group` on party doctypes
- After split, apply VTL/default: `customer_group = "All Customer Groups"` (or f3iche default)
- Add regression test: Customer payload from sundry ledgers must not contain `Sundry Debtors` as `customer_group`

**Impact on 4th_run**

Removes 2 of 5 blocking errors immediately without ERP site changes.

---

### 4. Supervisor “Continue with defaults” → real auto_fix (P0 trust)

**Problem**

Action `ask_user_ler_blocking_links` with option “Continue with defaults where possible” is type `ask_user`. Workflow re-runs validation without mutating payloads. `defaults.py` skips fields that are **non-empty**, so Tally values persist.

**Fix**

When `selected_option` matches continue/default patterns:

1. Emit companion **`auto_fix`** action (or handle in workflow) that runs:
   - VTL on all blocking `ler_gaps` from last validation report
   - `apply_kb_defaults` with **overwrite policy** for config link fields flagged blocking
   - Optional: SCB derive missing groups
2. Persist patched R2 payloads
3. Re-run `validate_mapped_data`
4. Only re-prompt if still blocking after auto_fix

**Supervisor action shape (target)**

```json
{
  "id": "auto_fix_ler_defaults",
  "type": "auto_fix",
  "scope": "validation",
  "changes": [
    { "target": "r2", "op": "apply_value_translation", "doctype": "Item", "fields": ["item_group"] },
    { "target": "r2", "op": "apply_value_translation", "doctype": "Customer", "fields": ["customer_group"] }
  ]
}
```

---

### 5. Unified supervisor UX (P3)

**Problem**

`SupervisorAttentionBanner` + `SupervisorPanel` / `PromptCard` duplicate prompts. Banner truncates to first sentence. Metadata `sample_gaps` / `ler_gaps` with exact values is persisted but **not rendered**. Note textarea requires action button; workflow ignores `user_note` for LER resolution.

**Fix**

| Change | Detail |
| ------ | ------ |
| Single surface | Banner becomes one line + “Open assistant”; full cards only in right panel |
| Gap card template | “**3 items** use group **Raw Materials** — not on your ERP. Map to: [dropdown of live Item Groups] [Use default]” |
| Chat parity | Chat messages that match continue/map intent invoke same `auto_fix` / VTL path as buttons |
| Note → action | Parse `user_note` for map intents (“use Raw Material”, “ignore sundry debtors”) via existing chat dispatcher + VTL |

---

### 6. Import preview checklist (P2 UX, uses existing data)

**Problem**

`Z_output.json` `ler_gaps` already distinguishes:

- `severity: "hint"` — will be created on import (Items, Customers, Projects on transactions)
- `severity: "blocking"` — must resolve first

Users never see this structured summary.

**Fix**

On Validate page / assistant:

```
Will create on your ERP:
  • 5 Items (from tally_stock_summary.csv)
  • 2 Customers, 2 Suppliers (from tally_sundry_ledgers.csv)
  • 2 Projects, 2 Sales Orders, …

Needs your OK (or auto-fix):
  • Item Group: Raw Materials (3 rows) → [Raw Material ▼]
  • Customer Group: Sundry Debtors (2 rows) → [All Customer Groups ▼]
```

Data source: validation report `ler_gaps` + mapped payload row counts — no new backend model required for v1.

---

### 7. Upload wave UX (celebrate what works)

**Problem**

3+3 upload pattern works (readiness 57% → 100%) but UI only shows generic “Re-upload round 2.”

**Fix**

- After union merge: toast + assistant message listing **new files** and **readiness delta**
- Obsolete prior supervisor prompts (already in workflow) — ensure UI clears stale cards
- Link to “what’s still missing” from readiness report if score < 100%

---

### 8. Golden matrix gate for 4th_run

**Problem**

Mapping fixes landed without a CI contract that **validate passes** on full 6-file corpus after live-ERP bootstrap or VTL dry-run.

**Fix**

Add golden matrix row(s):

| Corpus | Stage | Assert |
| ------ | ----- | ------ |
| `4th_run` | map | 6/6 files mapped; sundry → Customer+Supplier; stock → Item |
| `4th_run` | validate (mock LER) | 0 blocking after VTL + party semantics fix |
| `4th_run` | validate (live strahats) | 0 blocking after SCB or pre-seeded groups |

Fixture: `attachments/.../4th_run/Z_output.json` as expected blocking-before / pass-after reference.

Update [`GOLDEN_MATRIX_MANIFEST.md`](./GOLDEN_MATRIX_MANIFEST.md) and [`PRIORITIES.md`](./PRIORITIES.md) when shipped.

---

## MSME feature backlog (empathy-driven, post-P0)

Features MSMEs will ask for once the pipeline doesn’t loop on them:

| Feature | Why they care |
| ------- | ------------- |
| **Tally mode badge** | “We detected Tally export — ledger groups handled automatically.” |
| **Plain-language errors** | No “LER blocking link_target”; yes “Your customer list uses Tally group names.” |
| **Sandbox import first** | Try on copy site before live books — trust for first-time ERP users |
| **Session memory** | “Always use Litre” / “Our item group is Raw Material” saved for next upload wave |
| **Progress in human steps** | Mapping → Checking ERP → Ready to import — not Step 11 |
| **Post-import reconciliation** | “5 items created, 2 SOs submitted” vs uploaded counts |
| **Human handoff** | Escalate to implementer after N failed auto-fix cycles — MSMEs expect a person |
| **Regional language** | Hindi labels for critical gaps (India MSME) |
| **WhatsApp / email digest** | Optional — “Your import needs 1 click” (later; not launch blocker) |

---

## Product promise (what we can claim)

| Claim | Realistic? |
| ----- | ---------- |
| Any MSME, any file, zero config | **No** |
| MSME on supported **f3iche** (e.g. manufacturing chemical), Tally/Excel exports, standard ERPNext site | **Yes** — after VTL + SCB + supervisor honesty |
| MSME outside f3iche coverage | Discovery + custom target structure; slower path |
| Heavily customized ERPNext | More live-schema confirmation dropdowns |

**Moat:** messy real-world exports → correct records on **their** site, with explainable fixes — not infinite synonyms.

---

## Recommended sprint (align with PRIORITIES max-5)

| Priority | Item | Layer | Class | Status |
| -------- | ---- | ----- | ----- | ------ |
| P0 | Party-field semantics (`Under_Group` ≠ `customer_group`) | L3 / mapping | A | **Shipped** |
| P0 | VTL module + hook in defaults/supervisor | L3 (new) | B | **Shipped (Phase 0)** |
| P0 | Continue → `auto_fix` value translation | L1 / supervisor | A | **Shipped** |
| P1 | SCB activity + import plan Phase 0 | L2 / L4 | C | **Shipped (Phase 1)** |
| P1 | Validate gap cards + import preview from `ler_gaps` | L5 | A | **Shipped (Phase 1)** |

Branch: `feature/msme-vtl-phase-0`

After merge: update [`IS_V2_BACKLOG.md`](./IS_V2_BACKLOG.md) pillar lines and golden matrix manifest.

---

## Phase 0 shipped (code)

| Component | Path |
| --------- | ---- |
| VTL runtime | `containers/implementation/mapping_agent/value_translation.py` |
| VTL KB compose | `compose_value_translation()` in `schema/compose.py` |
| KB modules | `schema/value_translation/{index,erpnext_baseline,link_field_policies,tally}.json` |
| Party split guard | `is_common/party_rules.py` → `strip_split_column_from_field_mapping` |
| Mapping hooks | `mapping_agent/defaults.py`, `mapping_agent/activities.py` |
| Supervisor | `apply_value_translation` op in `supervisor_agent/activities.py` |
| Workflow | `is_workflow/workflow.py` — Continue with defaults → session VTL patch |

**Tests:** `test_value_translation.py`, `test_party_split_mapping_guard.py`

---

## Remaining KB research (manual — for you to fill)

Phase 0 ships scaffold + safe baseline rules. **No web scraping in code** — edit JSON after reviewing real exports.

### `schema/value_translation/tally.json`

Fill `field_value_maps` with Tally **cell values** (stock groups, regional UOM strings). Example:

```json
"Item": { "item_group": { "Consumables": "Consumable" } }
```

Do **not** map `Sundry Debtors` here — handled by `link_field_policies.json`.

### `schema/value_translation/erpnext_baseline.json`

Extend plural/singular maps (`Raw Materials` → `Raw Material` already done). Add `link_target_maps` when you catalog standard ERPNext group names.

### `schema/value_translation/link_field_policies.json`

Extend `party_ledger_class_values` for Busy/Zoho spelling variants if needed.

### Phase 1 (code, not JSON) — **Shipped**

Live ERP fuzzy match + Site Config Bootstrap (SCB) — see P1 rows above.

| Component | Path |
| --------- | ---- |
| SCB runtime | `containers/implementation/is_common/site_config_bootstrap.py` |
| SCB activity | `bootstrap_site_config` in `validation_agent/activities.py` |
| Import preview | `containers/implementation/is_common/import_preview.py` |
| Live fuzzy VTL | `fuzzy_match_live_erp()` in `mapping_agent/value_translation.py` |
| Config greenfield deferral | `ler_greenfield.py` + bootstrap coverage check |
| Workflow step 10b | `is_workflow/workflow.py` |
| Import plan Phase 0 | `finalize_import_plan` → `phase_0_site_config` |
| Validate UI | `ValidateView.tsx` import preview section |

**Tests:** `test_site_config_bootstrap.py`

After KB edits: `clear_cache()` then `pytest containers/implementation/tests/test_value_translation.py`.

---

## Appendix: 4th_run validation snapshot

From `Z_output.json` (2026-06-23):

**Blocking (5 errors → 2 root causes after dedup):**

- Item ×3: `Item Group 'Raw Materials' was not found on your live ERP site.`
- Customer ×2: `Customer Group 'Sundry Debtors' was not found on your live ERP site.`

**Passing doctypes:** BOM, Production Plan, Sales Order, Project, Supplier

**Hints (working greenfield):** FG items on BOM/Production Plan; customers/projects on Sales Order — “will be created during master import.”

**Note:** FG items use `item_group: "Finished Goods"` and did not block — likely already exists on `strahats.f3next.in`. Only `Raw Materials` (plural) failed — classic VTL fuzzy-match case (`Raw Material` singular).

---

## Related documents

- [`STRUCTURAL_FIXES_4TH_RUN.md`](./STRUCTURAL_FIXES_4TH_RUN.md) — mapping-layer fixes (plan gate, party split, corpus hints)
- [`ARCH_KNOWLEDGE_BASE.md`](./ARCH_KNOWLEDGE_BASE.md) — existing KB stack; VTL extends L3
- [`FOUNDATIONS.md`](./FOUNDATIONS.md) — L0–L5 triage; classify issues before PRs
