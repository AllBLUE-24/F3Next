# Implementation Pipeline Coherence Plan

> Status: structural implementation complete on `fix/is-pipeline-coherence`; live golden run pending  
> Scope: L1 truth contracts, L2 corpus spine, L3 target/field contracts, L4 import safety

## Implementation status

- Complete: confirmed target handoff and target-bounded mapping.
- Complete: canonical, persisted corpus assignment before readiness and mapping.
- Complete: fail-closed readiness, mapping, plan, status, and execution gates.
- Complete: dependency-action closure and Postgres MVP-scope fallback.
- Complete: F3iche field-vs-DocType policy separation and shared required-field resolver.
- Verified: implementation suite `191 passed, 2 skipped`; discovery suite
  `137 passed, 9 skipped`.
- Pending environment verification: rebuild the Temporal worker and execute a fresh
  project/session golden run against R2, Postgres, and ERPNext.

## Problem

The Discovery MVP boundary can be correct while the implementation still fails because
the confirmed target is not consistently carried into session-scoped activities and
multiple downstream nodes fail open. The result is scope drift, false readiness,
best-effort mapping, and unsafe import progression.

## Verified diagnosis

### Proven breaking points

1. **Project target was not materialized for the implementation session.**
   `load_project_target_structure` returned the correct project artifact to the
   workflow, while readiness, mapping, validation, and import queried
   `is_target_structures` by session. Missing session state then triggered fallback
   behavior.
2. **Mapping could escape the confirmed target.** Candidate doctypes always included
   a generic core set, and filename rules could override corpus assignments.
3. **Readiness fails open.** Missing target and empty manifest are represented as
   viable; workflow failures and supervisor-disabled paths continue to mapping.
4. **Progression-critical failures are logged as non-fatal.** Corpus enrichment,
   assignment, mapping, preliminary plan creation, site bootstrap, and persistence
   failures can still advance the stage.
5. **Import execution is not default-deny.** A required execution gate can be treated
   as confirmed when the supervisor is disabled; failed phases do not consistently
   stop later phases.
6. **Plan lifecycle errors are strings, not hard gates.** `error:*` finalization and a
   missing phase plan can still reach sandbox/import fallback behavior.
7. **MVP dependency actions are inconsistent.** Discovery graph closure can mark a
   conditional prerequisite such as BOM optional even when a selected Work Order
   requires it.
8. **MVP seed scope depends on the optional R2 mirror in import finalization.**
   Postgres remains canonical, but import can lose seeds/deferred doctypes when R2 is
   unavailable.
9. **Required-field truth is split.** Readiness scoring, matrix rendering, mapping,
   and validation resolve required fields through different paths.

### Earlier hypotheses corrected

- Building a preliminary plan before mapping is intentional: it creates
  `pending_mapping` placeholders. The defect is not its position alone; it is that
  creation/finalization failures do not block and missing plans fall back.
- Moving corpus assignment before readiness is insufficient by itself. It becomes a
  fix only when readiness consumes the same canonical assignment artifact.
- Business defaults are a quality risk, not the first root cause. Tightening them
  comes after target handoff and fail-closed contracts.

## Implementation sequence

### Phase 1 — Preserve the confirmed boundary

- Materialize the project target into the active `ISTargetStructure`.
- Load seeds/deferred doctypes from canonical Postgres when the R2 mirror is absent.
- Restrict mapping candidates to target doctypes; use generic core candidates only
  for explicit legacy/no-target fallback.
- Make corpus assignment authoritative over KB filename hints.
- Reconcile dependency setup actions during Discovery target generation.

Acceptance:

- A fresh session sees the same required, seed, deferred, setup, phase, and validation
  contracts as the project target.
- A file cannot map to a doctype outside the confirmed target.
- Work Order cannot have an optional BOM prerequisite.

### Phase 2 — Canonical corpus assignment

- Run assignment once after corpus understanding.
- Persist one versioned assignment artifact for the upload wave.
- Make readiness and mapping consume that artifact.
- Keep deterministic evidence/dry-run checks as validation of the assignment, not as
  competing classifiers.

Acceptance:

- Readiness, mapping, validation, and UI report the same file-to-doctype binding.
- An assignment disagreement is an explicit overclaim/block, not a silent reroute.

### Phase 3 — Fail-closed preparation gates

- Missing target, invalid manifest, failed corpus gate, or failed readiness returns a
  failed envelope with viability false.
- A non-viable readiness result blocks regardless of supervisor feature state.
- Supervisor controls how the user resolves a block; it does not control whether the
  invariant exists.
- Mapping with zero mapped files or failed MVP files cannot advance to validation.

Acceptance:

- No missing/failed preparation artifact can produce a green stage.
- Every user wait has a persisted stage and every system error terminates or blocks.

### Phase 4 — Import default-deny

- Treat all `error:*` plan statuses as blocked.
- Remove hardcoded phase fallback when no finalized plan exists.
- Require explicit execution confirmation whenever preflight requires it, independent
  of supervisor enablement.
- Abort remaining phases after any phase error or `steps_failed > 0`.
- Surface persistence failures for validation/import artifacts as activity failures.

Acceptance:

- No live write occurs without a finalized plan and required confirmation.
- Phase C cannot execute after Phase A/B failure.
- `complete` means all planned writes succeeded.

### Phase 5 — Unify field and default policy

- Route readiness, mapping preflight, validation, and import preflight through one
  required-field resolver.
- Split technical defaults from business-semantic assumptions.
- Technical defaults may be green; business assumptions remain partial until
  confirmed or proven from source/live ERP.

Acceptance:

- The readiness matrix and validation report list the same required fields.
- A business-semantic default cannot silently turn a blocking gap green.

### Phase 6 — Verification

1. Unit tests for target handoff, bounded classification, graph action closure,
   fail-closed status helpers, plan status, and phase abort.
2. Corpus, readiness, map/validate, and import package harnesses.
3. Temporal workflow integration tests for signal/gate ordering.
4. Fresh worker rebuild and a new project/session golden run.
5. Live checklist: compare project target, session target, assignment artifact,
   readiness matrix, mapped doctypes, finalized plan, and import results.

## Commit boundaries

1. Project target → session handoff.
2. Target-bounded canonical classification.
3. Discovery dependency-action closure and Postgres MVP-scope fallback.
4. Fail-closed corpus/readiness/mapping gates.
5. Import plan and execution default-deny.
6. Required-field/default-policy unification.
7. Workflow/harness verification and documentation closure.
