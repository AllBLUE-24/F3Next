# Test Harness — Automated Implementation Testing

## What this skill does

Automates end-to-end testing of F3Next's implementation pipeline by:
1. Creating test scenarios from F3iche archetypes
2. Running the full implementation workflow with simulated user interactions
3. Validating outputs at each stage (discovery → corpus → readiness → mapping → validation → import)
4. Diagnosing failures by F3Next layer (L0-L6)
5. Proposing and applying fixes with human approval

## When to use

- Testing new F3iche archetypes or pain patterns
- Regression testing after pipeline changes
- Debugging silent failures in the implementation workflow
- Validating fail-closed contracts and quality gates
- Creating reproducible test cases from production issues

## How to invoke

```
/test-harness [scenario_name] [--implement-fixes]
```

**Examples:**
```
# Run single scenario
/test-harness project-chemical-wip

# Run with auto-fix (requires human approval)
/test-harness project-chemical-wip --implement-fixes

# Generate new scenario from archetype
/test-harness --generate manufacturing/project/chemical "WIP visibility gaps"
```

---

## Instructions for Agent

You are a test automation specialist. Follow this workflow:

### Phase 1: Load or Generate Test Scenario

1. **If scenario name provided**: Load from `examples/{scenario_name}.json`
2. **If --generate flag**: Create new scenario:
   - Read F3iche KB from `shared/kb/f3iche/{archetype}.json`
   - Infer expected MVP seeds from pain point using `containers/discovery/target/build_target.py` logic
   - Generate corpus file stubs (filenames, expected doctypes, required columns)
   - Define expected gaps based on required fields
   - Save to `examples/{generated_name}.json`

**Scenario structure** (JSON):
```json
{
  "name": "project-chemical-wip",
  "context": {
    "company_name": "ChemTech Industries",
    "f3iche": "manufacturing/project/chemical",
    "pain_point": "WIP visibility gaps..."
  },
  "expected_mvp": {
    "seed_doctypes": ["Work Order", "BOM", "Item"],
    "deferred_doctypes": ["Quality Inspection"]
  },
  "corpus_files": [
    {"filename": "items.csv", "expected_doctype": "Item", "required_columns": [...]}
  ],
  "gap_responses": [
    {"field": "bom_no", "doctype": "Work Order", "value": "BOM-001"}
  ],
  "expected_record_counts": {"Item": 15, "BOM": 10}
}
```

### Phase 2: Setup Test Environment

1. **Create test project ID**: `TEST_{archetype}_{timestamp}` (e.g., `TEST_chemical_20260815_1503`)
2. **Initialize in Supabase**:
   - Insert into `projects` table with test prefix
   - Create `is_sessions` entry with `project_id`, `user_id`, `status="discovery"`
3. **Prepare workspace**: Create temp directory `results/test-run-{timestamp}/`

### Phase 3: Generate Corpus Files

For each `corpus_file` in scenario:

1. **Create CSV/Excel file**:
   - Use `required_columns` from scenario
   - Generate dummy data (10-15 rows)
   - Apply field coverage % (leave some fields blank to simulate gaps)
   - Save to `results/test-run-{timestamp}/corpus/{filename}`

**Example CSV generation**:
```csv
item_code,item_name,stock_uom,item_group
ITEM-001,Chemical A,Kg,Raw Material
ITEM-002,Chemical B,Ltr,
```

### Phase 4: Execute Discovery

1. **Start discovery chat**:
   - Use `backend/app/api/implementation.py` POST `/v1/implementation/discovery/chat`
   - Send scenario `pain_point` as user message
   - Continue chat until MVP boundary generated
2. **Capture discovery output**:
   - Read `ProjectTargetStructure` from Supabase `project_target_structures` table
   - Extract `target_structure_json.seed_doctypes`
3. **Validate (Discovery Oracle)**:
   - Compare actual seeds vs `expected_mvp.seed_doctypes`
   - Report: `PASS` if exact match, `FAIL` with diff otherwise

### Phase 5: Upload Corpus & Run Workflow

1. **Upload corpus files**:
   - POST to `/v1/implementation/sessions/{session_id}/upload` with generated files
   - Confirm files stored in R2 under `raw/{session_id}/`
2. **Trigger implementation workflow**:
   - Use `containers/implementation/is_launcher.py` or call Temporal workflow directly
   - Monitor workflow execution via `is_sessions.status`
3. **Wait for completion**:
   - Poll `is_sessions` table until `status IN ("completed", "failed", "blocked")`
   - Capture intermediate artifacts from R2 manifest

### Phase 6: Validate All Stages (Oracles)

For each pipeline stage, compare actual vs expected:

#### **Corpus Oracle**
- **Artifact**: `corpus_assignments` from R2 manifest or `is_sessions.file_batches`
- **Check**: Each file mapped to expected doctype
- **Pass condition**: `corpus_assignments[filename] == expected_doctype` for all files

#### **Readiness Oracle**
- **Artifact**: `DataReadinessAssessment` from workflow output
- **Check**: 
  - `minimum_viable_import_possible` matches expected
  - Gap fields identified match scenario `gap_responses`
- **Pass condition**: Viability correct + no phantom gaps

#### **Mapping Oracle**
- **Artifact**: Mapped CSV files in R2 `mapped/{session_id}/`
- **Check**: 
  - File count matches corpus file count
  - Column headers are ERPNext fieldnames
- **Pass condition**: All files mapped, no data loss

#### **Validation Oracle**
- **Artifact**: `validation_results` from workflow
- **Check**: Validation issues match `expected_validation_issues`
- **Pass condition**: No unexpected errors

#### **Import Oracle**
- **Artifact**: ERPNext database records (query via API)
- **Check**: Record counts per doctype match `expected_record_counts`
- **Pass condition**: All expected records created, links established

**Report format**:
```
=== Oracle Report ===
✅ Discovery: PASS (3/3 seed doctypes matched)
❌ Corpus: FAIL (items.csv mapped to BOM instead of Item)
⏸️  Readiness: SKIPPED (corpus failed)
...
First failure: Corpus (L2)
```

### Phase 7: Diagnose Failure (if any stage failed)

1. **Identify failure layer**:
   - Discovery fail → L0 (LLM) or L1 (boundary logic)
   - Corpus fail → L2 (corpus understanding)
   - Readiness fail → L3 (readiness assessment)
   - Mapping fail → L4 (mapping logic)
   - Validation fail → L5 (validation logic)
   - Import fail → L6 (import execution)

2. **Analyze root cause**:
   - Read relevant source files (e.g., `containers/implementation/mapping_agent/activities.py`)
   - Grep for related functions (e.g., `_should_map_doctype`, `assign_corpus_doctypes`)
   - Check recent changes in git history
   - Review `docs/plans/is-pipeline-coherence.md` for known issues

3. **Generate diagnostic report**:
```markdown
## Diagnostic Report

**Failed Stage**: Corpus
**Layer**: L2 (Corpus Understanding)
**Root Cause**: Filename prior override in `map_file_to_erpnext` is incorrectly 
prioritizing `_filename_doctype_override` over canonical `corpus_assignments`.

**Affected Code**:
- `containers/implementation/mapping_agent/activities.py` lines 245-260
- `assign_corpus_doctypes` not persisting authoritative assignment artifact

**Proposed Fix**:
1. Modify `_resolve_structured_file_doctype` to check `corpus_assignments` first
2. Ensure `assign_corpus_doctypes` saves assignment artifact to R2 manifest
3. Update `_get_candidate_doctypes` to respect target scope

**Files to Change**:
- containers/implementation/mapping_agent/activities.py
- containers/implementation/is_workflow/workflow.py (reorder activities)

**Test Coverage**:
- Add test: `test_canonical_assignment_beats_filename_prior`
```

### Phase 8: Apply Fixes (if --implement-fixes enabled)

1. **Human approval gate**:
   - Present diagnostic report to user
   - Ask: "Approve proposed fixes? (y/n)"
   - If rejected, stop and save report

2. **Apply code changes**:
   - For each proposed change:
     - Read current file content
     - Use `StrReplace` to apply modifications
     - Add regression test if specified
   - Create commit: `fix(test-harness): {fix_description}`

3. **Re-run test**:
   - Reset test environment (clean up previous artifacts)
   - Repeat Phase 3-6 with same scenario
   - If passes → SUCCESS, report fixed issue
   - If fails again → Retry diagnosis (max 3 iterations)

### Phase 9: Cleanup & Report

1. **Cleanup test artifacts**:
   - Delete test project from Supabase (if `config.json` cleanup enabled)
   - Delete R2 files under `TEST_` prefix
   - Delete ERPNext records (if staging environment)
   - Preserve artifacts on failure (for debugging)

2. **Save test result**:
```json
{
  "scenario": "project-chemical-wip",
  "status": "PASSED" | "FAILED" | "ERROR",
  "duration_seconds": 245.3,
  "first_failure_stage": "corpus",
  "oracle_scores": {
    "discovery": 1.0,
    "corpus": 0.6,
    "readiness": null
  },
  "diagnostic_report_path": "results/.../diagnostic.md",
  "fixed_by_iteration": 2
}
```

3. **Final report to user**:
```
✅ Test PASSED after 2 iterations
Fixed issue: Corpus mapping prioritization
Changes committed to: fix/test-harness-20260815-1503
Duration: 4m 5s

Review diagnostic: results/test-run-20260815-1503/diagnostic.md
```

---

## Configuration

Edit `config.json` for:
- **execution_mode**: `"offline"` (mocked) | `"workflow"` (real Temporal) | `"live"` (with ERPNext)
- **timeouts**: Per-stage timeout in seconds
- **cleanup**: Auto-delete test artifacts
- **oracle_strictness**: `"strict"` (exact match) | `"lenient"` (allow minor diffs)
- **max_fix_iterations**: Max auto-fix retry cycles

## Safety Guardrails

- ✅ Only touch projects with `TEST_` prefix
- ✅ Require human approval before applying fixes
- ✅ Clean up test artifacts automatically
- ✅ Never modify production data
- ✅ All fixes committed to feature branches (never main)
- ✅ Fail-safe: stop after max iterations (default 3)

## Example Scenarios

See `examples/` folder:
- `project-chemical-wip.json` — WIP visibility bottleneck
- (Add more scenarios as needed)

---

## Notes for Agent

- **Reuse existing F3Next components**: Don't reinvent file parsing, just call existing activities
- **Read `docs/FOUNDATIONS.md`** to understand layer classification
- **Reference `docs/plans/is-pipeline-coherence.md`** for known failure patterns
- **Use `containers/*/README.md`** step harnesses for offline validation
- **When stuck**: Ask user for clarification, don't guess
