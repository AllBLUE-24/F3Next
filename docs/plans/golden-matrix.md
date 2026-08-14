# Golden Matrix Manifest — Green Surface 3rd_run

> **Status:** Canonical acceptance matrix for v1.0.0-rc  
> **Layer:** L3 (ERP Knowledge) + L1 (Honesty)  
> **IS pillars:** 4 (Synonyms), 5 (ERP knowledge), 7 (Mapping), 9 (Validation)  
> **Fixtures:** `attachments/green-surface/greensurface_golden_data/3rd_run/`  
> **Harness:** `containers/implementation/tests/test_dry_run_map_3rd_run.py` (+ rows below)  
> **Related:** [`NORTH_STAR.md`](./NORTH_STAR.md) · [`ARCH_KNOWLEDGE_BASE.md`](./ARCH_KNOWLEDGE_BASE.md)

---

## 1. Purpose

**Stop blaming KB vs code in circles.** For the Green Surface beta corpus, every file and doctype in scope has a **manifest row**. If a row fails:

1. Classify **B (KB)** if synonym/child_fields/schema — fix KB + harness, not pipeline patches.  
2. Classify **A (code)** only after KB row documents the expected mapping and harness still fails.  
3. Classify **C** if pillar (e.g. drawer UI) not built — not a mapping bug.

**“IS is ready”** means: all **required** rows below are **green in CI** and **green on live Strahats** for one full loop.

---

## 2. Scope

| Dimension | Value |
|-----------|--------|
| **Customer** | Green Surface (golden); live tenant Strahats |
| **F3iche** | `manufacturing_project_chemical` |
| **Industry** | Manufacturing (chemical coatings / project installer) |
| **Upload wave** | `3rd_run` — 4 files (3 initial + `stock_entry.csv` on re-upload) |
| **MVP doctypes** | Customer, Supplier, Sales Order, Purchase Order, Stock Entry |
| **Out of scope for required rows** | Project, Item master files (derived/stubbed in validate), BOM, Work Order |

---

## 3. Corpus files

| File | Bytes (approx) | Role |
|------|----------------|------|
| `messy_partners.csv` | 207 | Party master split (Customer + Supplier) |
| `client_orders.csv` | 177 | Sales Order + project refs |
| `raw_purchase_orders.csv` | 214 | Purchase Order |
| `stock_entry.csv` | 180 | Stock Entry material issue to projects |

---

## 4. Per-file matrix

### 4.1 `messy_partners.csv`

| Field | Value |
|-------|--------|
| **Row ID** | `GM-FILE-01` |
| **Classify hint** | Multi-entity partners |
| **Target doctypes** | Customer (2 rows), Supplier (2 rows) |
| **Party split rule** | `Role` ∈ {Customer, Supplier, Vendor} |
| **Required columns → KB** | |

| CSV column | Customer field | Supplier field | KB synonym status |
|------------|----------------|----------------|-------------------|
| `Company_Name` | `customer_name` | `supplier_name` | ✅ `company_name` patterns |
| `Role` | split key | split key | ✅ |
| `City` | optional | optional | partial |
| `Contact` | optional | optional | strip if Contact not in scope |

| **Dry-run harness** | `test_dry_run_customer_from_party_split`, `test_dry_run_supplier_from_party_split` |
| **Map pass** | `passed=true`, 2 records each |
| **Preflight** | No blocking missing fields |
| **Validate (live)** | `partial` — LER warnings for names not yet in ERP (OK) |
| **Required** | ✅ Yes |

---

### 4.2 `client_orders.csv`

| Field | Value |
|-------|--------|
| **Row ID** | `GM-FILE-02` |
| **Target doctype** | Sales Order |
| **Required columns → KB** | |

| CSV column | ERP field / child | KB synonym status |
|------------|-------------------|-------------------|
| `Client` | `customer` | ✅ customer patterns |
| `Project` | `project` (link) | ⚠️ LER greenfield — warning OK |
| `Target_Date` | `delivery_date` | ✅ |
| `Product` | `items.item_code` | ✅ via fold |
| `Vol` | `items.qty` | ✅ volume/qty patterns |
| `Price` | `items.rate` | ✅ optional |

| **Dry-run harness** | `test_dry_run_sales_order_with_line_items` |
| **Map pass** | `passed=true`, 2 records, `items` present after fold |
| **Preflight** | `items` not in `missing_fields` |
| **Validate (live)** | `partial`, 0 errors — party stubs for New Age Builders |
| **Required** | ✅ Yes |

---

### 4.3 `raw_purchase_orders.csv`

| Field | Value |
|-------|--------|
| **Row ID** | `GM-FILE-03` |
| **Target doctype** | Purchase Order |
| **Required columns → KB** | |

| CSV column | ERP field / child | KB synonym status |
|------------|-------------------|-------------------|
| `PO_Number` | naming / ref | optional |
| `Vendor_Name` | `supplier` | ✅ |
| `Item` | `items.item_code` | ✅ |
| `Ordered_Qty` | `items.qty` | ✅ |
| `Price_Per_Unit` | `items.rate` | ✅ |

| **Dry-run harness** | `test_dry_run_purchase_order_with_line_items` |
| **Map pass** | `passed=true`, 3 records |
| **Preflight** | supplier + items present |
| **Validate (live)** | `partial` — stub Unknown Supplier Ltd |
| **Required** | ✅ Yes |

---

### 4.4 `stock_entry.csv` ✅ **RESOLVED**

| Field | Value |
|-------|--------|
| **Row ID** | `GM-FILE-04` |
| **Target doctype** | Stock Entry |
| **Stock entry type values** | `Material Issue` → ERP Stock Entry Type |
| **Required columns → KB** | |

| CSV column | ERP field / child | KB synonym status | Action |
|------------|-------------------|-------------------|--------|
| `stock_entry_type` | `stock_entry_type` | ✅ | — |
| `Project_Ref` | `project` | ✅ **FIXED** | Added `Project_Ref`, `project_ref` |
| `Item_Consumed` | `items.item_code` | ✅ **FIXED** | Added `Item_Consumed`, `item_consumed`, `material_consumed` |
| `Quantity` | `items.qty` | ✅ **FIXED** | Added `Quantity` (case-insensitive) |
| `Source_Whse` | `items.s_warehouse` | ✅ **FIXED** | Added `Source_Whse`, `source_whse`, `source_warehouse` |

| **Expected fold** | One Stock Entry per row OR grouped by `(stock_entry_type, project)` with `items[]` lines |
| **Dry-run harness** | `test_dry_run_stock_entry_with_line_items` — ✅ **PASSES** |
| **Map pass (target)** | ✅ `passed=true`, 2 records, `items` length ≥ 1 each |
| **Preflight (target)** | ✅ `items` not blocking |
| **Live status (2026-06-06)** | ✅ **GREEN** — all synonyms added, test harness passes |
| **Required** | ✅ Yes — MVP seed doctype for chemical project consumption |

**User-facing gap copy (when working):**

> `stock_entry.csv` mapped successfully. Material consumption will be tracked to projects.

---

## 5. End-to-end scenario rows

| Row ID | Scenario | Steps | Expected outcome | Required |
|--------|----------|-------|------------------|----------|
| `GM-E2E-01` | First upload (3 files) | Upload partners + orders + PO | Readiness &lt; 100%, supervisor asks for Stock Entry OR user uploads all 4 | ✅ |
| `GM-E2E-02` | Re-upload merge | Add `stock_entry.csv` | Corpus 4 files; readiness ≥ 85%; obsolete prior readiness prompt | ✅ |
| `GM-E2E-03` | Map all files | Auto map step 9 | 4/4 files mapped including Stock Entry | ✅ **GREEN** — target met |
| `GM-E2E-04` | Mapping confirm | User approves | `mapping_confirmed` | ✅ |
| `GM-E2E-05` | Validate | Step 11 | `overall=partial`, **errors=0**, warnings only (LER) | ✅ (run 2) |
| `GM-E2E-06` | Validation submit | User confirms on validate gate | `validation_submitted`; workflow advances | manual |
| `GM-E2E-07` | Import | Phased import | `steps_failed` honest in UI; SO/PO/Customer/Supplier commit | manual |

---

## 6. Doctype KB completeness (MVP set)

| Doctype | KB file exists | Golden column coverage | Child fold tested | Row |
|---------|----------------|------------------------|-------------------|-----|
| Customer | ✅ | GM-FILE-01 | n/a | required |
| Supplier | ✅ | GM-FILE-01 | n/a | required |
| Sales Order | ✅ | GM-FILE-02 | ✅ items | required |
| Purchase Order | ✅ | GM-FILE-03 | ✅ items | required |
| Stock Entry | ✅ | GM-FILE-04 | ✅ **FIXED** | **required** ✅ |
| Project | ✅ | deferred (link only) | n/a | optional |
| Item | ✅ | deferred (from SO/PO lines) | n/a | optional |

**KB promotion rule:** Any new CSV header seen in golden fixtures → `user_input_synonyms` on correct field within 24h of failure.

---

## 7. Harness contract

### 7.1 CI command

```bash
pytest containers/implementation/tests/test_dry_run_map_3rd_run.py -q
pytest containers/implementation/tests/test_ler_greenfield_3rd_run.py -q
pytest containers/implementation/tests/test_transactional_party_stubs.py -q
```

### 7.2 Required tests (add if missing)

| Test name | Asserts |
|-----------|---------|
| `test_dry_run_stock_entry_with_line_items` | Stock Entry fold + preflight pass |
| `test_golden_matrix_manifest_ids` | Meta-test: every `GM-FILE-*` has passing dry-run |

### 7.3 Live verify (Strahats)

Document in [`v1.0.0/FOUNDATION_VERIFICATION.md`](./v1.0.0/FOUNDATION_VERIFICATION.md):

- Project `2d21a137-...` or fresh GS project  
- Full loop through validation submit  
- Screenshot + workflow log archived

---

## 7b. Discovery MVP boundary (Step 1 gate)

> **Deterministic golden:** `pytest containers/discovery/test/test_mvp_boundary_golden.py -m golden`  
> **Live routing matrix (deterministic):** `pytest containers/discovery/test/test_live_routing_matrix.py -m routing_matrix`  
> **Live routing matrix (LLM):** `DISCOVERY_LIVE_MATRIX=1 pytest containers/discovery/test/test_live_routing_matrix.py -m live_llm`  
> **Harness batch:** `python -m containers.discovery.test.harness_mvp_boundary --matrix --report`  
> **Fixtures:** `containers/discovery/test/fixtures/`  
> **Matrices:** `golden_mvp_boundary.json` (scoping) · `live_routing_matrix.json` (LLM routing)  
> **Env gate:** `DISCOVERY_USE_MVP_MAP_FALLBACK=false`, `DISCOVERY_USE_LEGACY_REGEX_SCOPING=false`  
> **Step 1 complete:** GM-DISC-01..05 green **and** live matrix ≥80% (`gate_min_accuracy` in `live_routing_matrix.json`)

| Row ID | Scenario | F3iche | Archetype | Must include (Day-1) | Status |
|--------|----------|--------|-----------|----------------------|--------|
| **GM-DISC-01** | Green Surface WIP + Tally dual-system | `manufacturing_project_chemical` | `factory_wip_bridge` | Item, BOM, Work Order, Quality Inspection | ✅ Required |
| **GM-DISC-02** | Part A/B inventory + hazmat batch | `manufacturing_project_chemical` | `inventory_visibility` (signal) | Item, Batch, Stock Entry | ✅ Required |
| **GM-DISC-03** | ISO audit / quality gates | `manufacturing_project_chemical` | `incoming_quality_compliance` | Quality Inspection, Batch, Purchase Receipt | ✅ Required |
| **GM-DISC-04** | Custom order / quote CRM | `manufacturing_project_chemical` | `custom_order_pipeline` | Quotation, Sales Order, Project | ✅ Required |
| **GM-DISC-05** | Apex Resins recall + Tally dual-system | `manufacturing_project_chemical` | planner + `batch_expiration_obsolescence` ref | Batch, Customer, Delivery Note, Supplier or Purchase Receipt | ✅ Required |

### Live LLM routing matrix (`LR-DISC-*`)

| Row ID | Scenario | Expected archetype | Gate |
|--------|----------|-------------------|------|
| **LR-DISC-01** | Green Surface WIP / Tally black box | `factory_wip_bridge` | Live LLM |
| **LR-DISC-02** | Procurement / supplier lead times | `supplier_lead_time_variance` (+ alts) | Live LLM |
| **LR-DISC-03** | Toll subcontractor material leakage | `subcontracting_raw_material_leakage` | Live LLM + signal |
| **LR-DISC-04** | Field service dispatch chaos | `service_dispatch_chaos` (+ alts) | Live LLM |
| **LR-DISC-05** | ISO incoming quality | `incoming_quality_compliance` | Live LLM + signal |
| **LR-DISC-06** | Part A/B inventory | `inventory_visibility` | Live LLM + signal |
| **LR-DISC-07** | Custom order CRM | `custom_order_pipeline` | Live LLM + signal |
| **LR-DISC-08** | Site mix scrap | `scrap_yield_leakage` (+ alts) | Live LLM |
| **LR-DISC-09** | WIP / dual-system (alt archetypes OK) | `factory_wip_bridge` (+ alts) | Live LLM |
| **LR-DISC-10** | Golden WIP mirror | `factory_wip_bridge` | Deterministic niche only |

**Classify hint:** Failures here are **A (code)** if archetype_id + KB hints exist but scoping ignores them; **B (KB)** if Research archetype or `day1_seed_hints` missing; **C (LLM routing)** if deterministic golden passes but live matrix `<80%`.

---

## 8. Failure classification quick reference

| Symptom | Likely class | First action |
|---------|--------------|--------------|
| Column not mapped | **B** KB synonym | Update `Stock Entry.json` (etc.); add harness |
| `items` empty after map | **B** child fold + synonyms | KB + `fold_child_tables` path — ✅ RESOLVED (GM-FILE-04) |
| LER `unresolvable Customer` | **A** stub policy | `transactional_party_stubs` — expected warning |
| UI shows debug node name | **A** L5 | Presentation agent |
| Readiness 86% but map fails | **A** gate mismatch | Align readiness dry-run with map preflight rules |
| “Complete” with `steps_failed>0` | **A** L1 | Honesty contract |

---

## 9. Expansion policy (post-beta)

Adding a doctype to “supported” requires:

1. New row in this manifest (file or doctype section)  
2. KB mapping module with synonyms for **at least one** real customer CSV  
3. Dry-run test + preflight pass  
4. Entry in [`IS_V2_BACKLOG.md`](./IS_V2_BACKLOG.md) pillar 4 table  

**No** “supported doctypes” marketing claim without harness row.

---

## 10. Changelog

| Date | Change |
|------|--------|
| 2026-06-05 | Initial manifest from Green Surface 3rd_run live run + codebase audit |
| 2026-06-05 | GM-FILE-04 Stock Entry marked blocking — synonyms pending |
| 2026-07-06 | Added GM-DISC-01..04 Discovery MVP boundary golden rows + pytest gate |
| 2026-07-07 | Added LR-DISC-01..10 live routing matrix + ≥80% Step 1 gate |
| 2026-06-06 | ✅ **GM-FILE-04 RESOLVED** — Added synonyms (`Project_Ref`, `Item_Consumed`, `Quantity`, `Source_Whse`); test harness passes |

---

✅ **GM-FILE-04 and GM-E2E-03 are now GREEN!** Ready to update [`NORTH_STAR.md`](./NORTH_STAR.md) § Definition of Done and proceed toward `v1.0.0-rc` candidate.
