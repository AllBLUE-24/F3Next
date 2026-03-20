# Implementation System: How Data Gets Stored (for Parth)

This document explains the end-to-end Implementation flow in **F3Next** in very simple terms, with a special focus on:

1. Where the data is stored as you move from step to step
2. What `implementation_profile` actually is
3. Whether `company_profile` is stored somewhere separately
4. What each backend step outputs and what keys get saved

All details below are based on the current backend implementation code in:
`backend/app/api/implementation.py` and `backend/app/services/implementation/*`

---

## 0) The “big picture” (what the system is trying to do)

Implementation is the process of taking your existing ERP data (uploads) and converting it into:

1. The correct ERPNext setup plan for *your type of business* (F3iche)
2. Mapped data that fits ERPNext doctypes/fields
3. Validation results to avoid bad imports
4. A final import plan you can run in phases

The system does NOT just “think once”. It repeatedly:

- Extracts signals from files
- Infers business type (F3iche)
- Builds a target structure (setup order + validation rules)
- Maps your file columns to ERPNext fields
- Validates mapped data
- Produces a structured import plan
- Stores everything it learned in the project so the UI can show it later

---

## 1) The main storage places (where data lives)

### 1.1 Database: `projects.implementation_profile` (this is the main brain storage)

In the database, there is a `projects` table. Each project is a single transformation run for a company.

Your “company brain snapshot” is stored here:

- **Table column:** `projects.implementation_profile`
- **Type:** JSON

This JSON is versioned. Each important step can create a new version of the profile snapshot.

So: when you ask “what is `implementation_profile` and are we storing company_profile here?”

**Answer:** Yes. `implementation_profile` is the JSON snapshot that represents what the system calls the “company profile”.
There is no separate database column named `company_profile`.

The “company profile” is produced by `CompanyProfileService` and stored into `projects.implementation_profile`.

---

### 1.2 Database: `hooks` table (Discovery side, not Implementation side)

Discovery chat stores its state in the `hooks` table:

- `hooks.last_bot_response` (latest question)
- `hooks.extracted_tags` (detected tags)
- `hooks.discovery_metadata` (f3iche/industry/price plan)

Implementation does not primarily read from `hooks`. Instead, it uses the project’s Implementation data and the uploaded files/signals.

---

### 1.3 File storage: disk folder `uploads/` OR MinIO bucket

When the system receives actual file uploads, it stores the binary files in object storage.

There is a storage abstraction in:
`backend/app/core/storage.py`

Default behaviour (when MinIO is not used):

- **Storage type:** local disk
- **Folder:** `uploads/` at the repo root

When MinIO is enabled, it stores into a MinIO bucket instead.

The Ingestion endpoint (currently implemented) stores files like this:

`clients/{x_company_slug}/users/{x_user_slug}/ingestion/raw/YYYY/MM/DD/{uuid}_{file.filename}`

The API returns:

- `file_name`
- `object_path` (the path inside storage)

These returned values are exactly what the Implementation pipeline expects as `uploaded_files`.

---

## 2) What `implementation_profile` contains (exactly)

`projects.implementation_profile` stores the output of:
`CompanyProfileService.build_profile(...)`

That profile JSON is built with fields like:

- `project_id`
- `version` (incremented each time you update)
- `timestamp`
- `action` (`create` or `update`)

Core business identity:

- `f3iche` (business type/process niche)
- `industry` (industry classification from earlier steps)
- `industry_sub` (optional)

Company details (if user provides them):

- `company_size`
- `company_name`

F3iche derived deliverables (from `implementation/knowledge/f3iche_*.json`):

- `workflows` (names of workflows relevant to this F3iche)
- `modules` (required modules)
- `required_doctypes` (what ERPNext doctypes are required)

Discovery/Inference provenance:

- `f3iche_user` (what the user said)
- `f3iche_signals` (what the signals suggested)
- `f3iche_match_status` (`matched` / mismatch / clarification status)
- `uploaded_files` (list of files + object paths)
- `collected_signals` (extracted keywords/patterns)

Implementation outputs:

- `target_structure` (setup steps + validation rules + required doctypes)
- `field_mappings` (mapping results: doctype -> fields/values)
- `validation_report` (pass/fail + per-doctype issues)
- `import_phase` (what phase you are at in the import pipeline)

Important: `update_company_profile` stores a *full snapshot* of what you know so far.
So each update overwrites `projects.implementation_profile` with the new versioned snapshot.

---

## 3) Is “company_profile” stored separately?

No.

There is only one place in the DB for the company brain:

- `projects.implementation_profile`

In code terms:

- `CompanyProfileService` builds a “company profile object”
- the endpoint `POST /api/implementation/profile/update` stores it into `project.implementation_profile`

So `implementation_profile` == “company_profile” snapshot.

---

## 4) How the Implementation flow works (step by step, and how storage updates)

Below is the logical flow your system is designed for.
For each step, I list:

- What the backend endpoint does
- What it outputs
- What should be stored in `implementation_profile`

### Step A: Upload files (physical storage)

How it works:
- Files are uploaded to the backend (via an ingestion/upload mechanism)
- Files are stored into:
  - local `uploads/` OR MinIO
- Backend returns `uploaded_files` list with:
  - `file_name`
  - `object_path`

Where it is stored:
- Physical binaries: local disk or MinIO
- References: you store the returned `uploaded_files` list in `implementation_profile.uploaded_files`

---

### Step B: Brainstorm -> infer F3iche from files

Endpoint:
`POST /api/implementation/signals/infer`

Input:
- `project_id`
- `uploaded_files` (file_name + object_path expected)
- optional `file_contents` (filename -> extracted text)

What backend does:
- Reads `implementation/knowledge/signals_registry.json`
- Extracts signals from:
  - file names
  - and optionally file contents
- Scores each F3iche candidate

Output:
- `f3iche` (best candidate, e.g. trading/manufacturing/service)
- `confidence` (0.0 to 1.0)
- `collected_signals` (the extracted signals)

What gets stored next:
- `implementation_profile.f3iche_signals`
- `implementation_profile.collected_signals`
- `implementation_profile.uploaded_files`

This is part of the “company profile snapshot”.

---

### Step C: F3iche match verification (user vs signals)

Endpoint:
`POST /api/implementation/f3iche/verify`

Input:
- `f3iche_user` (what the user indicates, typically from Discovery output)
- `f3iche_signals` (the inferred f3iche from Step B)
- `confidence` (from Step B)

Output:
- `is_match` boolean
- `status` (`matched`, `mismatch`, or `pending_clarification`)
- `clarification_message` if mismatch

What gets stored next:
- `implementation_profile.f3iche_user`
- `implementation_profile.f3iche_signals`
- `implementation_profile.f3iche_match_status`

If mismatch occurs, the system needs clarification before proceeding.

---

### Step D: Build target structure (setup plan for ERPNext)

Endpoint:
`POST /api/implementation/target-structure`

Input:
- `f3iche`
- optional `industry`

What backend does:
- Loads F3iche definition from:
  - `implementation/knowledge/f3iche_*.json`
- Loads ERPNext doctype dependency graph from:
  - `implementation/knowledge/doctypes_graph_ERPNext.json`
- Creates:
  - a list of required doctypes
  - an ordered setup/import structure
  - validation rules (from the F3iche file)

Output:
- `target_structure` which includes:
  - `required_doctypes`
  - `setup_steps` (setup order with layer/phase)
  - `validation_rules`
  - and import phase structure

What gets stored next:
- `implementation_profile.target_structure`

---

### Step E: Map uploaded data -> ERPNext doctype/fields

Endpoint:
`POST /api/implementation/map-file`

Input:
- `content` (raw text of the file data)
- `filename`
- optional `doctype_hint`

What backend does:
- Uses `MappingEngine`:
  - guesses doctype by columns/headers
  - maps columns to ERPNext fields using:
    - `containers/operation_agent/knowledge/erpnext_field_mappings.json`
- For CSV-like content:
  - parses rows and returns structured row objects

Output:
- doctype inferred
- `field_mapping`
- `rows` (parsed table rows)
- `source_columns`

What gets stored next:
- `implementation_profile.field_mappings`

Note:
- The backend profile update expects `field_mappings` as JSON.
- The UI can store the `map-file` output in that key (or store only the relevant part).

---

### Step F: Validate mapped data

Endpoint:
`POST /api/implementation/validate`

Input:
- `mapped_data`
- `target_structure`

What backend does:
- Runs validation checks:
  - required field checks
  - date/numeric sanity warnings
  - collects errors and warnings

Output:
- `validation_report`:
  - `overall`: `pass` or `fail`
  - `checks`: per-doctype validation status
  - `errors` and `warnings`

What gets stored next:
- `implementation_profile.validation_report`

If validation fails, the UI should block import (or request fixes).

---

### Step G: Build the import plan (3 phases)

Endpoint:
`POST /api/implementation/import/plan`

Input:
- `target_structure`
- `mapped_data`
- `validation_report`

What backend does:
- If `validation_report.overall == fail`:
  - returns a blocked status
- Otherwise builds a 3-phase plan:
  - Phase A: configuration setup
  - Phase B: master data
  - Phase C: transactional data

Output:
- `import_plan`:
  - `status`: `ready` or `blocked`
  - `phases` with ordered steps
  - `total_steps`

What gets stored next:
- The current profile schema includes `import_phase`, but not an explicit `import_plan` field.
- In practice, you store what phase you are in via `implementation_profile.import_phase`,
  and you use `import_plan` directly to drive the next UI screen or import execution step.

---

## 5) Where “import into software” happens

In this codebase, the import engine can run in two modes:

1. **Dry-run / plan-only** (no ERPNext client configured)
2. **Actual import execution** (if an ERPNext client is configured)

From `ImportEngine.execute_phase(...)`:
- When no ERPNext client is provided:
  - it does not create docs
  - it returns a “dry_run” / “simulated” result

So the backend you currently have is primarily focused on:
- building import plans
- preparing mapping + validation
- driving the next phase of execution via other infrastructure

---

## 6) Important note: Frontend may use DEV mocks right now

Your frontend pages for Implementation (Analyze/Validate/Sandbox) include DEV-mode mocks.
That means during development:
- you may not see real backend-driven profile updates
- you will still see the UI flow “as if it computed everything”

But the backend implementation endpoints that actually do the real work are present and documented above:
- `/api/implementation/signals/infer`
- `/api/implementation/f3iche/verify`
- `/api/implementation/target-structure`
- `/api/implementation/map-file`
- `/api/implementation/validate`
- `/api/implementation/import/plan`
- `/api/implementation/profile/update`

When the frontend calls the real endpoints, the data is stored exactly as described:
into `projects.implementation_profile` and the `uploads/` or MinIO storage paths.

---

## 7) What Parth should remember (simple cheat sheet)

If you remember only 4 things, remember this:

1. **Uploaded files** go to `uploads/...` (local) or MinIO (object storage).
2. **References to files** (file_name + object_path) are stored inside:
   `projects.implementation_profile.uploaded_files`
3. **`implementation_profile` is the “company_profile snapshot”**:
   it is the single JSON place where the system stores what it learned and what it plans.
4. Each step produces outputs and those outputs are saved into specific keys:
   - signals -> `f3iche_signals`, `collected_signals`
   - target structure -> `target_structure`
   - mapping -> `field_mappings`
   - validation -> `validation_report`
   - import progress -> `import_phase`

