---
name: Phase 3 GreenSurface
overview: Onboard GreenSurface's "Project Manufacturing" use case purely by expanding the 3-Tier Context Engine — zero Python agent code changes required. Phase 2 de-hardcoding is confirmed complete and the engine is ready.
todos:
  - id: step1-graph
    content: "Expand erpnext_doctype_graph.json: add seeding_complexity+name_field to all existing doctypes, add layer_8_projects, add phase_mapping block, add ~25 new Phase D doctypes"
    status: completed
  - id: step2-f3iche
    content: Create containers/knowledge_base/common/f3iches/manufacturing_project_chemical.json with full business_reality, detection_signals, mandatory_doctypes, workflow_processes, and default_settings
    status: completed
  - id: step3-registry
    content: "Update signals_registry.json: add manufacturing_project_chemical to niche_ids, add project/chemical/coating signal rules, add niche_score_to_id_map entry"
    status: completed
  - id: step4-fieldmaps
    content: Add party_type_synonyms and doctype_keyword_hints top-level keys to field_mappings.json
    status: completed
  - id: step5-chunks
    content: Write project_manufacturing_kb_chunks.py with 20 priority KB chunks covering batch chemical manufacturing and project site execution
    status: completed
  - id: step6-seed
    content: Update seed_kb.py to import and include ALL_PROJECT_MANUFACTURING_CHUNKS in the master_list
    status: completed
  - id: step7-fixtures
    content: Create infer_f3iche_greensurface.json, update build_target_structure.json f3iche value, create execute_import_phase_d.json; update is_harness.py --phase choices
    status: completed
  - id: step8-validate
    content: "Run full validation sequence: seed_kb → infer_f3iche → verify_f3iche → build_target_structure → build_import_plan → execute_import_phase (dry-run Phase D)"
    status: in_progress
isProject: false
---

# Phase 3: GreenSurface Onboarding via Context Expansion

## Architecture Confirmation

Phase 2 is verified complete. Key mechanisms are already in place:

- **Dynamic phases**: `_ImportEngine.build_plan()` already reads phases from `setup_steps` and auto-creates `phase_d_projects` entries when found.
- **Seeding flexibility**: `_is_seed_blacklisted()` already reads `seeding_complexity` from the graph JSON before consulting the static fallback.
- **Name field discovery**: `_discover_name_field()` checks `_DT_NAME_FIELD` first, then falls back to a live Frappe API call — new Phase D doctypes need no Python entry.
- **F3iche validation**: `_F3icheVerificationService.verify()` uses prefix matching (`manufacturing_`*) — registering a new niche in `signals_registry.json` is sufficient for detection. 

---

## Step 1 — Expand `erpnext_doctype_graph.json`

**File**: `[containers/knowledge_base/erpnext/erpnext_doctype_graph.json](containers/knowledge_base/erpnext/erpnext_doctype_graph.json)`

**What changes:**

**1a. Add `seeding_complexity` and `name_field` to ALL existing doctypes**

Every existing doctype entry gets two new fields. This is what unlocks `_is_seed_blacklisted()` to read from the graph rather than the static fallback:

```json
"UOM": {
  "seeding_complexity": "simple",
  "name_field": "uom_name",
  ...
},
"BOM": {
  "seeding_complexity": "complex",
  ...
},
"Company": {
  "seeding_complexity": "skip",
  ...
}
```

**1b. Add new `layer_8_projects` to `setup_layers` block**

```json
"layer_8_projects": ["Project", "Task", "Timesheet", "Project Template", "Activity Type"]
```

**1c. Add `phase_d_projects` phase mapping block**

```json
"phase_mapping": {
  "phase_a_config":        ["layer_0_system", "layer_1_config"],
  "phase_b_master":        ["layer_2_masters", "layer_3_parties"],
  "phase_c_transactional": ["layer_4_pricing", "layer_5_transactions", "layer_6_fulfillment", "layer_7_finance"],
  "phase_d_projects":      ["layer_8_projects"]
}
```

**1d. Add ~25 new doctypes for GreenSurface**

New entries, each with `layer`, `phase`, `seeding_complexity`, `name_field`, `depends_on`, `required_fields`, `sme_relevance`:

- **Layer 2 (config masters)**: `Workstation`, `Operation`, `Activity Type`, `Activity Cost`, `Department`, `Designation`, `Asset Category`, `Project Template`
- **Layer 3 (parties)**: `Employee`
- **Layer 4**: `Quality Inspection Template`
- **Layer 5**: `Subcontracting Order`, `Asset`
- **Layer 6**: `Quality Inspection`, `Batch`, `Maintenance Schedule`, `Subcontracting Receipt`
- **Layer 7**: `Landed Cost Voucher`, `Issue`
- **Layer 8 (Phase D)**: `Project`, `Task`, `Timesheet`, `Timesheet Detail`, `Project Update`

Each Phase D doctype gets `"phase": "phase_d_projects"`.

**1e. Extend `module_to_doctype_map`**

```json
"Projects": ["Project", "Task", "Timesheet", "Project Template", "Activity Type", "Activity Cost"],
"HR": ["Employee", "Department", "Designation"],
"Assets": ["Asset", "Asset Category", "Maintenance Schedule"]
```

---

## Step 2 — Create the F3iche Definition

**File (new)**: `[containers/knowledge_base/common/f3iches/manufacturing_project_chemical.json](containers/knowledge_base/common/f3iches/manufacturing_project_chemical.json)`

Structure mirrors `manufacturing_food_batch.json` exactly. Key values:

- `"id": "manufacturing_project_chemical"`
- `"display_name": "Project Manufacturing — Specialty Chemicals / Construction Coatings"`
- `**mandatory_doctypes`**: 32-entry list including all Phase A/B/C doctypes PLUS `Project`, `Task`, `Timesheet`, `Batch`, `Quality Inspection`, `Workstation`, `Employee`
- `**detection_signals.strong_signals.column_headers**`: `["project code", "site address", "installation date", "batch no", "epoxy", "pu coating", "substrate"]`
- `**detection_signals.strong_signals.file_names**`: `["project list", "site costing", "batch register", "installation record"]`
- `**workflow_processes**`: Two processes:
  - `P1_batch_chemical_manufacturing`: BOM → Work Order → Quality Inspection → FG
  - `P2_project_site_execution`: Project → Material Issue → Timesheet → Milestone Invoice
- `**absolute_profile.mandatory_modules**`: `["Manufacturing", "Projects", "Stock", "Selling", "Buying", "Accounts", "HR"]`
- `**default_settings**`: FIFO valuation, batch tracking enabled, project costing enabled, composite GST handling
- `**notes_for_ai_agent**`: Dual-mode operations instructions — when to route to Phase D vs Phase C

---

## Step 3 — Register New F3iche in Signals Registry

**File**: `[containers/knowledge_base/common/signals_registry.json](containers/knowledge_base/common/signals_registry.json)`

**3a. Add to `_meta.niche_ids`**

```json
"niche_ids": [
  ...,
  "manufacturing_project_chemical"
]
```

**3b. Add new signal rules** to `file_name_signals`, `column_header_signals`, and `sheet_name_signals` that point to `"manufacturing_project_chemical"`:

- File name: `["project list", "site costing", "installation record", "batch register", "epoxy", "coating", "floor coating"]`
- Column header: `["project code", "project name", "site address", "installation date", "coating type", "substrate", "batch no"]`
- Sheet name: `["Projects", "Site Expenses", "Batch Register", "Installation", "Project Costing"]`

**3c. Add to `niche_score_to_id_map`**

```json
"manufacturing_project_chemical": {
  "key_discriminating_signals": ["project list + batch register both present", "installation/site columns", "coating product names (epoxy, PU, vinyl ester)", "dual BOM+project costing"],
  "minimum_score_for_confident_match": 0.70
}
```

---

## Step 4 — Extend `field_mappings.json`

**File**: `[containers/knowledge_base/erpnext/schema/field_mappings.json](containers/knowledge_base/erpnext/schema/field_mappings.json)`

Add two top-level keys used by `mapping_agent` and `validation_agent`:

```json
"party_type_synonyms": {
  "client": "Customer",
  "buyer": "Customer",
  "end user": "Customer",
  "purchaser": "Customer",
  "vendor": "Supplier",
  "seller": "Supplier",
  "subcontractor": "Supplier",
  "employee": "Employee"
},
"doctype_keyword_hints": {
  "project": "Project",
  "site work": "Project",
  "installation": "Project",
  "timesheet": "Timesheet",
  "batch": "Batch",
  "quality inspection": "Quality Inspection",
  "workstation": "Workstation",
  "work order": "Work Order",
  "asset": "Asset"
}
```

---

## Step 5 — Write 20 Priority KB Chunks

**File (new)**: `[containers/knowledge_base/project_manufacturing_kb_chunks.py](containers/knowledge_base/project_manufacturing_kb_chunks.py)`

Structured identically to `manufacturing_kb_chunks.py` (list of category dicts, each with `industry`, `kb_type`, and `chunks` array).

20 priority chunks:

1. Batch Production in ERPNext for Chemical Manufacturing
2. BOM Management for Epoxy/PU Formulations
3. Batch Expiry and Shelf Life for Chemicals
4. Quality Inspection for Chemical Batches
5. Raw Material Management (Resins, Hardeners, Pigments)
6. Work Order and Job Card for Batch Production
7. Batch-wise Costing and Variance Analysis
8. Production Planning: Make-to-Stock + Make-to-Order
9. Project Setup in ERPNext for Site Installation Services
10. Material Estimation and Allocation for Site Projects
11. Project-wise Costing and Profitability Tracking
12. Labor, Subcontractor, and Equipment Management in Projects
13. Project Milestones and Payment Schedules
14. Project Completion, Handover, and Warranty
15. Stock Reservation for Projects (Material vs Free Stock)
16. Transfer from Manufacturing Stock to Project Stock
17. Dual Sales Process (Product Invoice vs Project Invoice)
18. Integration: Manufacturing Module + Projects Module in ERPNext
19. Composite Supply GST Invoicing for Project-Based Businesses
20. Dual Costing Architecture (Product Costing + Project Costing)

---

## Step 6 — Update `seed_kb.py`

**File**: `[containers/knowledge_base/seed_kb.py](containers/knowledge_base/seed_kb.py)`

One import added + one list extended — no logic changes:

```python
from containers.knowledge_base.project_manufacturing_kb_chunks import ALL_PROJECT_MANUFACTURING_CHUNKS
# ...
master_list = ALL_MANUFACTURING_CHUNKS + ALL_TRADING_CHUNKS + ALL_PROJECT_MANUFACTURING_CHUNKS
```

---

## Step 7 — Create GreenSurface Harness Fixtures

**File (new)**: `[containers/implementation/dev_fixtures/infer_f3iche_greensurface.json](containers/implementation/dev_fixtures/infer_f3iche_greensurface.json)`

Simulates GreenSurface file signals without R2 upload:

```json
{
  "uploaded_files": [
    {"file_name": "greensurface_items.csv"},
    {"file_name": "batch_register_2025.xlsx"},
    {"file_name": "project_list_fy2025.xlsx"},
    {"file_name": "customer_list.csv"},
    {"file_name": "bom_epoxy_flooring.xlsx"}
  ],
  "r2_manifest_url": "",
  "session_id": ""
}
```

**File (update)**: `[containers/implementation/dev_fixtures/build_target_structure.json](containers/implementation/dev_fixtures/build_target_structure.json)`

Change `"f3iche"` value from `"trading"` to `"manufacturing_project_chemical"`.

**File (new)**: `[containers/implementation/dev_fixtures/execute_import_phase_d.json](containers/implementation/dev_fixtures/execute_import_phase_d.json)`

```json
{
  "session_id": "PASTE-REAL-SESSION-UUID-HERE",
  "project_id": "PASTE-REAL-PROJECT-UUID-HERE",
  "phase_id": "phase_d_projects",
  "dry_run": true
}
```

Also update `is_harness.py` `--phase` choices to include `"phase_d_projects"` (this is a test tool, not an agent).

---

## Step 8 — End-to-End Validation

Run in sequence after KB is re-seeded:

```bash
# Seed the new chunks into pgvector
python -m containers.knowledge_base.seed_kb

# Step 1: Verify niche detection
python -m containers.implementation.is_harness \
  --step infer_f3iche \
  --fixture dev_fixtures/infer_f3iche_greensurface.json \
  --mock-llm
# Expected: f3iche = "manufacturing_project_chemical"

# Step 2: Verify F3iche registration
python -m containers.implementation.is_harness \
  --step verify_f3iche \
  --fixture dev_fixtures/verify_f3iche.json
# (update fixture: f3iche_user + f3iche_signals = "manufacturing_project_chemical")

# Step 3: Verify target structure includes Phase D doctypes
python -m containers.implementation.is_harness \
  --step build_target_structure \
  --fixture dev_fixtures/build_target_structure.json \
  --mock-llm
# Expected: setup_steps includes Project, Task, Batch, Quality Inspection

# Step 4: Verify import plan generates Phase D
python -m containers.implementation.is_harness \
  --step build_import_plan \
  --fixture dev_fixtures/build_import_plan.json
# Expected: plan.phases includes "phase_d_projects"

# Step 5: Dry-run Phase D execution
python -m containers.implementation.is_harness \
  --step execute_import_phase \
  --fixture dev_fixtures/execute_import_phase_d.json \
  --dry-run
# Expected: All Phase D steps execute with dry_run=True, no ERPNext writes
```

**Success Criteria:**

1. `infer_f3iche` returns `manufacturing_project_chemical` with confidence ≥ 0.70
2. `build_target_structure` includes `Project`, `Task`, `Batch`, `Quality Inspection` in `setup_steps`
3. `build_import_plan` produces a plan where `phases` contains `phase_d_projects`
4. `execute_import_phase` (dry-run) completes Phase D without errors
5. Zero Python agent file modifications across the entire Phase 3 execution

