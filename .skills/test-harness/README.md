# Test Harness Architecture

## Overview

The test harness automates end-to-end testing of F3Next's implementation pipeline by simulating realistic user interactions and validating system outputs against expected states.

## Design Principles

1. **Scenario-Driven** — Tests are declarative JSON scenarios defining company context, pain points, expected MVP, corpus files, and gap responses
2. **Oracle-Based Validation** — Each pipeline stage has a dedicated oracle that diffs expected vs actual outputs
3. **Layer-Aware Triage** — Diagnostician classifies failures by F3Next layer (L0-L6) and proposes targeted fixes
4. **Human-in-Loop** — All structural changes require explicit approval before implementation
5. **Reuse Existing Assets** — Leverages F3iche KB, step harnesses, smoke tests, and live Temporal workflows

## Components

### 1. Scenario Author (`scenario_author.py`)

**Purpose**: Generate test cases from F3iche archetypes or convert live sessions to reproducible scenarios.

**Inputs**:
- F3iche archetype (e.g., `manufacturing/project/chemical`)
- Pain point (e.g., "WIP visibility", "stock shortages")
- Optional: Live session ID to replay

**Outputs**:
- `TestScenario` JSON with:
  - Company context (name, industry, size, archetype)
  - Pain point description (for discovery chat)
  - Expected MVP boundary (seed doctypes, deferred doctypes)
  - Corpus file stubs (with expected doctype assignments)
  - Gap response templates (for data readiness loop)

**Logic**:
```python
def generate_scenario(f3iche: str, pain: str) -> TestScenario:
    # 1. Load F3iche KB for archetype
    kb = load_f3iche_kb(f3iche)
    
    # 2. Generate expected MVP from pain + KB
    expected_mvp = infer_mvp_from_pain(pain, kb)
    
    # 3. Create corpus file stubs
    corpus_files = generate_corpus_stubs(expected_mvp.seed_doctypes)
    
    # 4. Generate expected gaps from required fields
    expected_gaps = compute_expected_gaps(expected_mvp, corpus_files)
    
    # 5. Create gap response templates
    gap_responses = generate_gap_responses(expected_gaps)
    
    return TestScenario(
        context=...,
        pain_point=pain,
        expected_mvp=expected_mvp,
        corpus_files=corpus_files,
        gap_responses=gap_responses
    )
```

### 2. Simulated User (`simulated_user.py`)

**Purpose**: Respond to system prompts (file uploads, data gaps) using scenario-defined templates.

**Capabilities**:
- Generate CSV/Excel files matching corpus stubs
- Answer data gap questions from scenario templates
- Handle multi-turn discovery chat for bottleneck clarification
- Inject realistic data quality issues (missing fields, format errors)

**Logic**:
```python
class SimulatedUser:
    def respond_to_upload_prompt(self, schema: dict) -> list[str]:
        # Generate files matching upload_schema_preview
        return self._generate_corpus_files(schema)
    
    def respond_to_gap_question(self, gap: dict) -> str:
        # Lookup answer from scenario gap_responses
        return self._get_gap_response(gap)
    
    def respond_to_discovery_chat(self, question: str) -> str:
        # Use LLM with scenario context to answer clarifications
        return self._answer_discovery_question(question)
```

### 3. Oracle (`oracle.py`)

**Purpose**: Validate pipeline outputs against scenario expectations at each stage.

**Oracles**:

#### Discovery Oracle
- **Input**: Discovery output (`ProjectTargetStructure`)
- **Expected**: `scenario.expected_mvp.seed_doctypes`
- **Validation**:
  - All expected seeds present in `target_structure_json`
  - No unexpected seeds (scope creep)
  - Dependency actions correctly inferred (`must_create` for transitive deps)

#### Corpus Oracle
- **Input**: Corpus assignment artifact (`corpus_assignments`)
- **Expected**: `scenario.corpus_files[].expected_doctype`
- **Validation**:
  - Each file mapped to expected doctype
  - No unmapped files (if expected to map)
  - No out-of-scope doctypes assigned

#### Readiness Oracle
- **Input**: Readiness assessment (`DataReadinessAssessment`)
- **Expected**: `scenario.expected_gaps`
- **Validation**:
  - All expected gaps identified
  - No phantom gaps (false positives)
  - `minimum_viable_import_possible` matches expected viability

#### Mapping Oracle
- **Input**: Mapped CSV files in R2 (`mapped/`)
- **Expected**: `scenario.expected_mappings`
- **Validation**:
  - All expected files mapped
  - Column mappings correct (ERPNext fieldnames)
  - No data loss during transformation

#### Validation Oracle
- **Input**: Validation report (`validation_results`)
- **Expected**: `scenario.expected_validation_issues`
- **Validation**:
  - All expected issues flagged
  - No false positives (over-validation)
  - Link errors correctly detected

#### Import Oracle
- **Input**: ERPNext database records
- **Expected**: `scenario.expected_records`
- **Validation**:
  - Correct number of records created per doctype
  - Field values match expected (spot check key fields)
  - Links between records established correctly

**Output**: `OracleReport` with pass/fail per stage, diff details, and divergence point.

### 4. Diagnostician (`diagnostician.py`)

**Purpose**: Triage oracle failures and propose structural fixes.

**Logic**:
```python
def diagnose(oracle_report: OracleReport, scenario: TestScenario) -> DiagnosticReport:
    # 1. Identify divergence point
    failed_stage = oracle_report.first_failure_stage
    
    # 2. Classify by F3Next layer
    layer = classify_failure_layer(failed_stage, oracle_report.diff)
    
    # 3. Determine fix type
    if layer == "L0":  # LLM prompt/router
        fix_type = "prompt_refinement"
    elif layer in ["L1", "L3", "L4", "L5"]:  # Boundary/readiness/mapping/validation logic
        fix_type = "structural_change"
    elif layer == "L2":  # Corpus understanding
        fix_type = "kb_promotion"
    else:  # L6 (import execution)
        fix_type = "import_policy_change"
    
    # 4. Propose specific changes
    proposed_changes = generate_fix_plan(layer, fix_type, oracle_report.diff)
    
    return DiagnosticReport(
        layer=layer,
        fix_type=fix_type,
        root_cause=...,
        proposed_changes=proposed_changes,
        confidence=...
    )
```

**Classification**:
- **L0** — LLM prompt/router (e.g., MVP seeds wrong due to pain point misclassification)
- **L1** — Boundary logic (e.g., `build_target` missing transitive deps)
- **L2** — Corpus understanding (e.g., file-doctype assignment wrong)
- **L3** — Readiness logic (e.g., gap analysis missing required field)
- **L4** — Mapping logic (e.g., column mapping incorrect)
- **L5** — Validation logic (e.g., false positive link error)
- **L6** — Import execution (e.g., ERPNext API error)

**Fix Types**:
- **Structural** — Code change in pipeline logic (preferred)
- **KB Promotion** — Add override to F3iche KB (acceptable for archetype-specific quirks)
- **Patch** — Hardcoded workaround (last resort, requires tech debt ticket)

### 5. Test Runner (`test_runner.py`)

**Purpose**: Orchestrate full test loop.

**Algorithm**:
```python
def run_test_harness(scenario_name: str, implement_fixes: bool = False):
    # 1. Load scenario
    scenario = load_scenario(scenario_name)
    
    # 2. Initialize simulated user
    user = SimulatedUser(scenario)
    
    # 3. Run pipeline
    session = start_implementation_session(scenario.context)
    discovery_result = run_discovery_with_user(session, user)
    corpus_result = run_corpus_with_user(session, user)
    readiness_result = run_readiness_with_user(session, user)
    mapping_result = run_mapping(session)
    validation_result = run_validation(session)
    import_result = run_import(session)
    
    # 4. Run oracles
    oracle = Oracle(scenario)
    report = oracle.validate_all(
        discovery_result,
        corpus_result,
        readiness_result,
        mapping_result,
        validation_result,
        import_result
    )
    
    # 5. If failed, diagnose
    if not report.all_passed:
        diagnostician = Diagnostician()
        diagnosis = diagnostician.diagnose(report, scenario)
        
        # 6. Human gate
        if implement_fixes:
            if ask_user_approval(diagnosis):
                apply_fixes(diagnosis.proposed_changes)
                # Recursive retry
                return run_test_harness(scenario_name, implement_fixes)
        
        return TestResult(status="failed", oracle_report=report, diagnosis=diagnosis)
    
    return TestResult(status="passed", oracle_report=report)
```

## Data Models

See `schemas.py` for full Pydantic definitions. Key models:

- `TestScenario` — Declarative test case
- `ExpectedMVP` — Seed doctypes, deferred doctypes, dependency graph
- `CorpusFileStub` — Filename, expected doctype, field coverage %
- `GapResponseTemplate` — Question pattern, answer template
- `OracleReport` — Pass/fail per stage, diff details
- `DiagnosticReport` — Layer, fix type, root cause, proposed changes
- `TestResult` — Final outcome, artifacts, logs

## Integration Points

### Temporal Workflows
- Reuses `ImplementationWorkflow` for live execution
- Runs in test project context (`TEST_` prefix)
- Mocks external dependencies (ERPNext) in offline mode

### F3iche KB
- Loads archetype policies from `shared/kb/f3iche/`
- Uses `always_ask_doctypes`, `defer_doctypes_until_post_mvp`, `always_ask_fields`
- Scenario author references KB to generate expected MVPs

### Step Harnesses
- Reuses `containers/*/README.md` step harnesses for offline validation
- Oracle compares live outputs to harness expected outputs

### Smoke Tests
- Runs `python -m shared.smoke_llm` as pre-flight check
- Fails fast if L0 router is broken

## Execution Modes

### Offline Mode
- Mocks Temporal activities with synchronous Python calls
- Uses in-memory DB (SQLite) instead of Supabase
- Mocks R2 with local filesystem
- Mocks ERPNext with dummy API responses
- Fast (seconds per test), good for unit-level validation

### Workflow Mode
- Runs real Temporal workflows against local worker
- Uses test Supabase database
- Uses test R2 bucket
- Mocks ERPNext API
- Slower (minutes per test), validates orchestration logic

### Live Mode
- Full integration test against staging ERPNext
- Uses staging Supabase + R2
- Creates real ERPNext records (cleaned up after)
- Slowest (10+ minutes per test), validates end-to-end correctness

## Safety Guardrails

1. **Test Project Isolation**: All sessions use `TEST_` project ID prefix
2. **Artifact Cleanup**: R2 files and DB records deleted after run (unless `--preserve-artifacts`)
3. **ERPNext Safeguards**: Never runs against production instance (staging URL hardcoded)
4. **Human Approval Gate**: Diagnostician proposals require explicit user confirmation
5. **Feature Branch Isolation**: All fixes committed to `fix/test-harness-*` branches
6. **Rollback on Fail**: If fix doesn't resolve issue after 3 retries, reverts changes

## Future Enhancements

1. **Batch Mode**: Run all F3iche scenarios in parallel, generate coverage matrix
2. **Performance Profiling**: Track execution time per stage, identify bottlenecks
3. **Mutation Testing**: Inject errors in corpus/gaps to validate error handling
4. **Regression Suite**: Auto-generate scenarios from past prod failures
5. **CI Integration**: Run subset of scenarios on every PR (fast offline mode)
