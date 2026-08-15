# Test Harness — Automated Implementation Testing

## What this skill does

Runs automated end-to-end testing of F3Next's implementation pipeline using:
1. **Scenario Authoring** — Create test cases from F3iche archetypes and pain points
2. **Simulated User** — Generate realistic corpus files and gap responses
3. **Backend Oracles** — Verify system outputs against expected DB/R2/API states
4. **Diagnostician** — Triage failures and propose structural fixes
5. **Implementor Loop** — Apply fixes and re-test until pass

## When to use

- Testing new F3iche archetypes or MVPs
- Regression testing after pipeline changes
- Debugging silent failures in discovery/corpus/readiness/import
- Validating fail-closed contracts and quality gates
- Generating reproduction scenarios from live sessions

## How to invoke

```
/test-harness [scenario_name] [--thorough] [--implement-fixes]
```

**Options:**
- `scenario_name` — Name of test scenario in `examples/` or generate new
- `--thorough` — Run all F3iche variations, not just core
- `--implement-fixes` — Auto-apply diagnostician recommendations (requires human gate)

**Examples:**
```
# Run single scenario
/test-harness project-chemical-wip

# Generate and run all manufacturing scenarios
/test-harness --thorough manufacturing

# Run with auto-fix (human review before apply)
/test-harness project-chemical-wip --implement-fixes
```

## How it works

### 1. Scenario Selection/Generation
- Reads scenario from `examples/` or generates from F3iche KB
- Defines company context, pain points, expected MVP, corpus files, gaps

### 2. Simulated Execution
- Runs discovery chat with scenario pain point
- Generates/uploads corpus files as simulated user
- Responds to data gap questions with scenario-defined answers
- Executes full pipeline: discovery → corpus → readiness → mapping → validation → import

### 3. Oracle Validation
- **Discovery Oracle**: MVP boundary matches expected seed doctypes
- **Corpus Oracle**: File-doctype assignments match expected mapping
- **Readiness Oracle**: Gap list matches expected missing fields
- **Validation Oracle**: Mapped data passes import validation
- **Import Oracle**: Records created in ERPNext match expected structure

### 4. Diagnostician Triage
On failure:
- Identifies exact step and artifact where divergence occurred
- Classifies issue: L0 (LLM), L1 (boundary logic), L2 (corpus), L3 (readiness), L4 (mapping), L5 (validation), L6 (import)
- Proposes fix type: structural (preferred), KB promotion (acceptable), patch (last resort)
- Generates implementation plan with file changes and test coverage

### 5. Human Gate + Implementation
- Presents diagnostician report for review
- Waits for human approval to implement
- Applies fixes, commits to feature branch
- Re-runs scenario to verify fix
- Loops until pass or max iterations

## Configuration

Edit `config.json` for:
- Test environment (local Temporal worker, staging ERPNext)
- Timeout thresholds per step
- Oracle strictness levels
- Auto-implement vs manual review mode
- Log verbosity

## File structure

```
.skills/test-harness/
├── SKILL.md                  # This file
├── README.md                 # Architecture overview
├── config.json               # Test configuration
├── schemas.py                # Pydantic models for scenarios/results
├── scenario_author.py        # Generate test cases from F3iche KB
├── simulated_user.py         # Respond to system prompts
├── oracle.py                 # Validate outputs against expected
├── diagnostician.py          # Triage failures, propose fixes
├── test_runner.py            # Main orchestrator
├── examples/                 # Pre-built test scenarios
│   ├── project-chemical-wip.json
│   ├── jobshop-scheduling.json
│   └── ...
└── results/                  # Test run outputs (gitignored)
    ├── 2026-08-15-143012/
    │   ├── scenario.json
    │   ├── oracle_report.json
    │   ├── diagnostician_report.md
    │   └── logs/
    └── ...
```

## Integration with F3Next

- Uses existing `containers/implementation/is_workflow/` for execution
- Reads F3iche KB from `shared/kb/f3iche/`
- Validates against live Supabase/R2/ERPNext (or mocked in offline mode)
- Reuses `shared.smoke_llm` for L0 validation
- Follows `docs/FOUNDATIONS.md` layer classification

## Safety

- Runs against test project IDs only (prefix `TEST_`)
- Cleans up R2/DB artifacts after each run (unless `--preserve-artifacts`)
- Never touches production ERPNext instance
- Diagnostician proposals require human approval before implementation
- All fixes committed to feature branches, never main

## Next steps

After running test harness:
1. Review `results/latest/diagnostician_report.md`
2. Approve/reject proposed fixes
3. If approved, skill creates branch `fix/test-harness-YYYYMMDD-HHMMSS`
4. Verify fix via re-run, then merge to main

## Status

**Prototype** — Core loop functional, oracles for discovery/corpus/readiness.
**TODO**: Import oracle, ERPNext validation, multi-scenario batch mode.
