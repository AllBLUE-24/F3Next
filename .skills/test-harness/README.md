# Test Harness — Overview

## Purpose

Automates end-to-end testing of F3Next's implementation pipeline using scenario-based validation and layer-aware diagnostics.

## How It Works

### 1. Test Scenario Definition

Scenarios are JSON files defining:
- Company context (F3iche archetype, pain point)
- Expected MVP boundary (seed doctypes, deferred doctypes)
- Corpus files to generate (filenames, expected assignments)
- Gap responses (how to answer data readiness questions)
- Expected outcomes (record counts, validation issues)

**Example**: `examples/project-chemical-wip.json`

### 2. Test Execution Flow

```
Load Scenario
     ↓
Create TEST_ Project → Generate Corpus Files
     ↓
Run Discovery Chat → Validate MVP Boundary (Oracle 1)
     ↓
Upload Corpus → Run Workflow → Extract Assignments (Oracle 2)
     ↓
Check Readiness → Validate Gaps (Oracle 3)
     ↓
Run Mapping → Validate Mapped Files (Oracle 4)
     ↓
Run Validation → Check Errors (Oracle 5)
     ↓
Run Import → Verify ERPNext Records (Oracle 6)
     ↓
All Pass? → SUCCESS
     ↓
Any Fail? → Diagnose by Layer (L0-L6)
     ↓
Propose Fixes → Human Approval → Apply → Retry
```

### 3. Oracle Validation

Each pipeline stage has an oracle that compares actual vs expected:

| Stage | Validates | Pass Condition |
|-------|-----------|----------------|
| **Discovery** | MVP boundary | Seed doctypes match expected |
| **Corpus** | File-doctype assignments | Each file mapped correctly |
| **Readiness** | Data gaps | Viability + gap list accurate |
| **Mapping** | Mapped CSVs | All files transformed, no data loss |
| **Validation** | Import validation | Expected errors identified |
| **Import** | ERPNext records | Record counts match per doctype |

### 4. Layer-Aware Diagnosis

Failures are classified by F3Next architecture layer:

- **L0** (LLM) — Prompt/router issues → Fix: Refine prompts
- **L1** (Boundary) — MVP generation logic → Fix: Update `build_target.py`
- **L2** (Corpus) — File understanding → Fix: Corpus assignment logic
- **L3** (Readiness) — Gap analysis → Fix: Required fields resolution
- **L4** (Mapping) — Doctype routing → Fix: Candidate restriction
- **L5** (Validation) — Import validation → Fix: Validation predicates
- **L6** (Import) — ERPNext execution → Fix: Import phase handling

### 5. Fix Application Loop

1. Agent analyzes failure, reads relevant code
2. Proposes specific changes (file paths, modifications)
3. **Human approval gate** — User reviews diagnostic report
4. If approved: Apply fixes, commit to feature branch, re-run test
5. If passes: SUCCESS, report fixed issue
6. If fails again: Re-diagnose (max 3 iterations)

## File Structure

```
.skills/test-harness/
├── SKILL.md              # Agent instructions (this is what the agent reads)
├── README.md             # This file (overview for humans)
├── config.json           # Execution mode, timeouts, cleanup settings
└── examples/             # Pre-defined test scenarios
    ├── project-chemical-wip.json
    └── ...
```

## Usage

```bash
# Run a scenario
/test-harness project-chemical-wip

# Run with auto-fix (requires approval)
/test-harness project-chemical-wip --implement-fixes

# Generate new scenario from archetype
/test-harness --generate manufacturing/project/chemical "Stock shortage visibility"
```

## Configuration (`config.json`)

```json
{
  "execution_mode": "workflow",  // offline | workflow | live
  "timeouts": {
    "discovery_seconds": 120,
    "corpus_seconds": 180,
    ...
  },
  "oracle_strictness": {
    "discovery": "strict",       // strict | lenient
    "corpus": "strict",
    ...
  },
  "diagnostician": {
    "max_fix_iterations": 3,
    "require_human_approval": true,
    "create_feature_branch": true
  },
  "cleanup": {
    "delete_test_projects": true,
    "preserve_on_failure": true
  }
}
```

## Execution Modes

### Offline Mode
- Fast (seconds per test)
- Mocks Temporal activities
- Uses in-memory DB
- Good for: Rapid iteration on test scenarios

### Workflow Mode (Recommended)
- Real Temporal workflows
- Test Supabase + R2
- Mocked ERPNext
- Good for: Validating orchestration logic

### Live Mode
- Full integration test
- Staging ERPNext
- Slow (10+ minutes)
- Good for: Pre-production validation

## Safety

✅ Only touches `TEST_` prefixed projects  
✅ Requires human approval for structural changes  
✅ Cleans up artifacts automatically  
✅ Commits fixes to feature branches (never main)  
✅ Max iteration limit prevents infinite loops  

## Integration with F3Next

- Reads F3iche KB from `shared/kb/f3iche/`
- Uses existing Temporal workflows (`ImplementationWorkflow`)
- Validates against live Supabase/R2/ERPNext (or mocks)
- Follows `docs/FOUNDATIONS.md` layer classification
- References `docs/plans/is-pipeline-coherence.md` for known issues

## Example Scenario

See `examples/project-chemical-wip.json`:
- Tests WIP visibility bottleneck for chemical manufacturing
- Expected MVP: Work Order, BOM, Item
- Corpus: 3 files (items.csv, bom.xlsx, work_orders.csv)
- Expected gaps: bom_no, planned_start_date, item_group
- Expected outcome: 15 Items, 10 BOMs, 12 Work Orders in ERPNext

## Next Steps

1. Run existing scenario: `/test-harness project-chemical-wip`
2. Review diagnostic report if fails
3. Add more scenarios for other F3iche archetypes
4. Use for regression testing after pipeline changes
