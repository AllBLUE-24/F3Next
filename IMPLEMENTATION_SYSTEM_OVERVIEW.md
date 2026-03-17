# F3 Implementation System — Architecture & Approach

**Document Purpose:** High-level overview of the implementation system for co-founder alignment. No code—structure, flow, and deliverables only.

---

## 1. F3iche (Niche) Definition & Files

**What it is:** A **F3iche** is a business-process-based niche. It groups companies by *similar workflows and processes*, not by industry.

**Examples:**
- Electronics trader + Pharma/Medical trader → **same F3iche** (both are trading/distribution workflows)
- Manufacturing + Retail → different F3iches (different process flows)

**Deliverable:** One file per F3iche containing:
- Workflow definitions for that process type
- Required modules and doctypes for that F3iche
- Process-specific setup and validation rules

**Output:** `f3iche_<name>.json` (or equivalent) per niche.

---

## 2. Discovery: Consultant Chatbot

**Purpose:** Understand the company before any technical setup.

**Flow:**
1. Chatbot acts as an ERP consultant
2. Asks about:
   - Company size
   - Industry
   - Core work / processes
   - Pain points and goals
3. Recommends:
   - Best ERP software (future: multi-ERP support)
   - Price plan
4. **Output:** Initial F3iche candidate + Industry classification

**Output:** User-provided F3iche + Industry from conversation.

---

## 3. Cross-Verification: `signals_registry.json`

**Purpose:** Validate and refine F3iche using uploaded company data.

**How it works:**
- **signals_registry.json** maps patterns found in uploaded files → F3iche candidates
- Agent scans all uploaded files
- Collects signals (keywords, structures, formats, document types)
- Scores each F3iche against collected signals
- Selects highest-confidence F3iche match

**Output:** System-inferred F3iche from file analysis.

---

## 4. F3iche Match Verification

**Purpose:** Ensure user intent and system inference align.

**Flow:**
1. Compare:
   - F3iche from chatbot (user-provided)
   - F3iche from signals_registry (file-based inference)
2. **If match:** Proceed
3. **If mismatch:** Ask user for clarification before proceeding

**Output:** Confirmed F3iche + Industry (single source for downstream steps).

---

## 5. Industry-Specific Knowledge (Vector DB)

**Purpose:** Provide domain-aware context for mapping and validation.

**Storage:**
- Industry-specific knowledge in vector databases
- Used for semantic search, field mapping, and validation hints

**Output:** Retrievable industry context for agents and workflows.

---

## 6. Company Profile & Company Context

**Purpose:** Central, versioned view of the company for the implementation.

**Contents:**
- F3iche + Industry (confirmed)
- Company size, structure
- Discovered workflows and processes
- Uploaded file metadata and signals
- Any user preferences or constraints

**Versioning:** Updated after every significant action (upload, mapping, validation, import step).

**Output:** `company_profile.json` (or equivalent) — versioned, single source of truth for company context.

---

## 7. Doctype Dependency Graph: `doctypes_graph_ERPNext.json`

**Purpose:** Single source of truth for ERPNext structure.

**Contains:**
- Doctype relationships and dependencies
- Field requirements per doctype
- Module memberships
- Setup order (what must exist before what)

**Usage:** Agent uses this to:
- Validate company data structure
- Determine correct setup order
- Ensure dependencies are satisfied before import

**Output:** `doctypes_graph_ERPNext.json` — static reference, ERPNext-specific.

---

## 8. Target Structure (Action Workflow)

**Purpose:** Define the exact implementation plan for this company.

**Flow:**
1. Use F3iche workflow definition
2. Use doctypes_graph for dependencies
3. Use company profile for constraints
4. **Finalize:** Actual action workflow (what to create, in what order, with what data)

**Output:** THE TARGET STRUCTURE — ordered list of setup steps and data mappings.

---

## 9. Company Data Mapping to ERPNext

**Purpose:** Map user-provided data fields to ERPNext doctypes and fields.

**Input:**
- User-uploaded data (CSV, Excel, Tally, etc.)
- Target structure
- Doctype graph
- Industry knowledge (for ambiguous mappings)

**Output:** Field-level mapping (source → ERPNext doctype.field).

---

## 10. Validation

**Purpose:** Ensure mappings and data are correct before import.

**Checks:**
- Data type compatibility
- Required fields present
- Referential integrity (e.g., Customer exists before Sales Order)
- Business rules (e.g., dates, amounts)
- Duplicate detection

**Output:** Validation report — pass/fail per entity, with errors and suggestions.

---

## 11. Import (3-Phase)

**Purpose:** Load data in the correct order to satisfy ERPNext dependencies.

### Phase A: CONFIGURATION SETUP (No user data yet)

**Creates:**
- Chart of Accounts (from Tally COA or default India COA)
- Item Groups, Customer Groups, Supplier Groups
- Warehouses
- Tax Templates
- Fiscal Year
- Company settings

**Output:** Base configuration ready for master and transactional data.

---

### Phase B: MASTER DATA

**Creates:**
- Items
- Customers
- Suppliers
- BOMs (if manufacturing F3iche)

**Output:** Master records in place for transactional references.

---

### Phase C: TRANSACTIONAL DATA

**Creates:**
- Opening Balances (special handling)
- Historical transactions (optional — last 3 months only)

**Output:** Company is live with historical context where applicable.

---

## Summary: End-to-End Flow

| Step | Input | Output |
|------|-------|--------|
| 1 | — | F3iche files (workflow + modules per niche) |
| 2 | User conversation | F3iche + Industry (user-provided) |
| 3 | Uploaded files + signals_registry | F3iche (system-inferred) |
| 4 | User + System F3iche | Confirmed F3iche + Industry |
| 5 | — | Industry knowledge in vector DB |
| 6 | All above | Company Profile + Context (versioned) |
| 7 | — | doctypes_graph_ERPNext.json |
| 8 | F3iche + Graph + Profile | Target Structure (action workflow) |
| 9 | User data + Target + Graph | Field-level mapping |
| 10 | Mapped data | Validation report |
| 11 | Validated data | 3-phase import (Config → Master → Transactional) |

---

## Deliverables Checklist (for Co-Founder)

- [x] **F3iche files** — `implementation/knowledge/f3iche_trading.json`, `f3iche_manufacturing.json`, `f3iche_service.json`
- [x] **Consultant chatbot** — Discovery flow extended with F3iche + Industry + ERP recommendation (in `discovery_metadata`)
- [x] **signals_registry.json** — `implementation/knowledge/signals_registry.json`
- [x] **Match verification** — `F3icheVerificationService` + `/api/implementation/f3iche/verify`
- [ ] **Vector DB** — Industry-specific knowledge (placeholder; can add Chroma/Pinecone later)
- [x] **Company Profile & Context** — `Project.implementation_profile` (versioned JSONB)
- [x] **doctypes_graph_ERPNext.json** — `implementation/knowledge/doctypes_graph_ERPNext.json`
- [x] **Target Structure** — `TargetStructureService` + `/api/implementation/target-structure`
- [x] **Mapping engine** — `MappingEngine` + `/api/implementation/map-file`
- [x] **Validation engine** — `ValidationEngine` + `/api/implementation/validate`
- [x] **3-phase import** — `ImportEngine` + `/api/implementation/import/plan`

---

## Implementation Notes

**Database migration:** Run `backend/migrations/add_implementation_columns.sql` to add `implementation_profile` (projects) and `discovery_metadata` (hooks).

**API base:** All implementation endpoints under `/api/implementation/`.

**Frontend:** `frontend/src/lib/api/implementation_api.ts` — client for all implementation APIs.

---

*Document version: 1.1 | Implementation complete*
