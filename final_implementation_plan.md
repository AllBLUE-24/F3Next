# FINAL IMPLEMENTATION PLAN: Restoring F3Next Context-Driven Architecture
### To: CEO | From: CTO | Date: 2026-05-03

---

## Executive Summary & Verification Statement

I have personally re-audited the agent codebases (`workflow.py`, `import_agent`, `signals_agent`, `validation_agent`, `mapping_agent`). 

**The diagnosis is verified and confirmed:** The architecture is fundamentally sound and aligns with your LLM-first, context-driven vision. The core engine is capable of scaling to any F3iche without backend changes. 

However, **8 critical "band-aids" (hardcoded Python logic)** were introduced during rapid MVP development. These band-aids bypass the knowledge base and force the system to act rigidly, particularly breaking our ability to support GreenSurface's "Project Manufacturing" phase.

This document serves as the final, approved implementation plan to strip out these 8 violations and return the system to a 100% data-driven state. After execution, the backend becomes a pure executor; all business logic will live exclusively in the JSON/pgvector context.

---

## Phase 1: Context Infrastructure Expansion (Day 1)
*Goal: Prepare the JSON files to hold the logic that is currently hardcoded in Python.*

### 1.1 Update `erpnext_doctype_graph.json`
*   **Add Seeding Metadata:** Add `"seeding_complexity": "simple" | "complex" | "skip"` to all existing doctypes.
*   **Add Name Fields:** Add `"name_field": "fieldname"` to simple doctypes.
*   **Add GreenSurface Doctypes (25+):** 
    *   **Projects:** `Project`, `Project Task`, `Project Template`, `Task`, `Timesheet`, `Timesheet Detail`
    *   **Manufacturing:** `Batch`, `Quality Inspection`, `Quality Inspection Template`, `Workstation`, `Operation`
    *   **Others:** `Employee`, `Asset`, `Asset Category`, `Maintenance Schedule`, `Landed Cost Voucher`, `Subcontracting Order`, `Subcontracting Receipt`
*   **Add New Phase Mapping:** Map a new layer to `phase_d_projects`.

### 1.2 Update `schema/field_mappings.json`
*   **Add Entity Synonyms:** Create a `"party_type_synonyms"` object to map terms like "client" to "Customer" and "vendor" to "Supplier".
*   **Add Keyword Hints:** Create a `"doctype_keyword_hints"` object for unstructured text inference.
*   **Add Enum Options:** Ensure all enum fields (e.g., `payment_type`) have `"fieldtype": "Select"` and their respective `"options"` defined.

### 1.3 Update `signals_registry.json`
*   **Register New F3iche:** Add `"manufacturing_project_chemical"` to `_meta.niche_ids`.

---

## Phase 2: Code De-Hardcoding (Day 2)
*Goal: Remove the 8 Python violations and wire them to read from the updated context files.*

### Violation 1 & 2: The 3-Phase Bottleneck
*   **Location:** `is_workflow/workflow.py` (line 760) & `import_agent/activities.py` (line 332)
*   **Issue:** The system hardcodes Phases A, B, and C. It will drop Phase D (Projects).
*   **Fix:** 
    *   In `_ImportEngine.build_plan()`, dynamically generate the `phases` dictionary by reading the `phase` keys from the incoming `setup_steps`.
    *   In `workflow.py`, before the import loop, read the phases directly from the generated `ISImportPlan` instead of a static array.

### Violation 3: F3iche Normalization Erasure
*   **Location:** `signals_agent/activities.py` (line 127)
*   **Issue:** `NORMALIZE_MAP` crushes specific F3iches (like `manufacturing_project_chemical`) down to generic `"manufacturing"`.
*   **Fix:** Delete `NORMALIZE_MAP`. Update `_F3icheVerificationService.verify()` to validate against the `niche_ids` list in `signals_registry.json` and use string prefix matching for broad categorization.

### Violation 4 & 5: Seeding Logic Hardcodes
*   **Location:** `import_agent/activities.py` (lines 51 & 177)
*   **Issue:** `_DYNAMIC_SEED_BLACKLIST` and `_DT_NAME_FIELD` dictate how to create records, breaking on new doctypes.
*   **Fix:** Delete both dicts. Refactor the agent to read `"seeding_complexity"` and `"name_field"` directly from the `erpnext_doctype_graph.json` lookup.

### Violation 6: Hardcoded Validation Rules
*   **Location:** `validation_agent/activities.py` (line 37)
*   **Issue:** `REQUIRED_FIELDS` and `ENUM_FIELDS` are hardcoded in the class.
*   **Fix:** Delete these dicts. Inject `graph` and `field_mappings` into `_ValidationEngine`. Read required fields from the graph and enum rules from `field_mappings.json` (where `fieldtype == "Select"`).

### Violation 7 & 8: Hardcoded Mapping Fallbacks
*   **Location:** `mapping_agent/activities.py` (lines 123 & 233)
*   **Issue:** `ENTITY_TYPE_VALUES` and `_keyword_infer_doctype` hardcode how to guess doctypes and split files.
*   **Fix:** Delete the hardcodes. Have `_MappingEngine` read `"party_type_synonyms"` and `"doctype_keyword_hints"` from `field_mappings.json`.

---

## Phase 3: GreenSurface Onboarding (Day 3-5)
*Goal: Use the newly unfettered architecture to support the new client via context alone.*

### 3.1 Create F3iche Definition
*   **File:** `f3iches/manufacturing_project_chemical.json`
*   **Action:** Define detection signals, mandatory doctypes (including Projects/Batch), workflow processes, and default settings.

### 3.2 Build Industry Knowledge Base
*   **Action:** Write the initial 20 priority KB chunks covering batch manufacturing, project site operations, composite GST, and dual costing.
*   **Execution:** Run `seed_kb.py` to embed these into the `pgvector` store.

### 3.3 End-to-End Validation Run
*   **Action:** Run `is_harness.py` against GreenSurface sample data.
*   **Success Criteria:** 
    1.  `infer_f3iche` identifies `manufacturing_project_chemical`.
    2.  `build_target_structure` pulls in Project and Batch doctypes.
    3.  `build_import_plan` dynamically generates a Phase D for Projects.
    4.  Workflow executes all phases without a single code modification.

---

## Verification Sign-off
I have verified this plan against the codebase. Executing this will permanently resolve the architectural drift and restore the system to a state where future clients only require knowledge base updates. 

Ready to begin execution of Phase 1 upon your approval.
