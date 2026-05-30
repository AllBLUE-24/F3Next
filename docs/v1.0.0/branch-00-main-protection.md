# Branch 00 — `main` (Protection & Hotfix Lane)

> **Git branch:** `main`  
> **Role:** Production-safe baseline; receives cherry-picks only when foundation work is not ready.  
> **Does not carry:** Large foundation refactors until `v1.0.0-rc` merge.

---

## 1. Purpose

`main` is the **deployable spine** while foundation branches experiment. It may receive:

- **P0 hotfixes** that unblock production (workflow sandbox, deps).  
- **Docs-only** updates that do not change runtime contracts.  
- **Final merge** of `foundation/frontend-contracts` → tag `v1.0.0-rc`.

It must **not** accumulate half-finished LER or gate refactors that break workers without coordinated deploy.

---

## 2. What stays on `main` until rc merge

| Component | State |
|-----------|--------|
| Temporal workflows | Stable activity names; existing signal names |
| `shared/os_field_semantics.py` | Incremental fixes allowed if backward compatible |
| KB JSON | Promoted rules only (no experimental stubs) |
| Frontend | Current honesty fixes if isolated |

---

## 3. Allowed changes on `main` (without foundation branch)

### 3.1 Class D — ops / deps

- `containers/os/requirements.txt` — `openai` / `httpx` pin alignment (done in program).  
- Worker rebuild documentation in runbook.  
- Environment variable fixes for ERP credentials.

### 3.2 Class A — P0 hotfixes (cherry-pick from `foundation/os-brain`)

| Fix | Files | Verification |
|-----|-------|--------------|
| Temporal sandbox crash on validation repair | `containers/os/os_workflow/workflow.py` — remove `shared/os_field_semantics` import; use `workflow_gates.py` static autofill list | OS command with fixable validation error completes repair path |
| Confirm API unreachable | Investigate `POST /api/os/confirm/{id}` routing, CORS, worker registration | Network tab shows 200; workflow receives signal |

**Hotfix branch name:** `hotfix/os-workflow-sandbox` → PR to `main` only.

### 3.3 Class B — KB promotion

- `os_validation.json` changes that **only** add autofill / policies already implemented in semantics.  
- Must include golden matrix row or unit test reference.

---

## 4. Forbidden on `main` (use foundation branches)

| Change | Target branch |
|--------|---------------|
| New `resolve_entities` activity + workflow reorder | `foundation/os-brain` |
| `shared/entity_resolution` package | `foundation/shared-platform` |
| IS supervisor / readiness unified COMPLETE | `foundation/is-brain` |
| Validator switch CVS → `link_cache` authority | `foundation/os-brain` |
| Frontend gate result types overhaul | `foundation/frontend-contracts` |

---

## 5. Protection rules for agents & humans

1. **Max 5 active** items in [`PRIORITIES.md`](../PRIORITIES.md); foundation work counts.  
2. **No UI `complete`** when `steps_failed > 0` — even on `main`.  
3. **After L0 LLM change:** `python -m shared.smoke_llm`.  
4. **Triage required** on every PR: layer, pillar, class, gate.  
5. **Filename-only priors** rejected without KB promotion path.

---

## 6. Merge gates into `main`

Before any foundation branch merges:

| Gate | Owner |
|------|-------|
| All tests in branch doc § Verification | Author |
| Worker rebuild noted in PR | Author |
| `RELEASE_v1_0_0.md` checklist rows ticked | Reviewer |
| No regression on `main` deploy smoke | Ops |

**Order for full program:** see [`BRANCH_STRATEGY.md`](./BRANCH_STRATEGY.md) — typically merge `frontend-contracts` last as single rc PR or sequential merges.

---

## 7. Ideation: how `main` users experience interim state

Between hotfixes and rc:

- OS may still show CVS-stale errors for UI-created masters → **document known limitation** in pilot comms until `os-brain` deploys.  
- IS may still have duplicate gap scanners → acceptable until `is-brain`.  
- Product version string may still say “beta” internally → customer-facing flips at **tag**.

---

## 8. Checklist (branch owner: release captain)

- [ ] P0 hotfix path documented and tested  
- [ ] `main` CI green on default pipeline  
- [ ] No foundation feature flags half-enabled in production env  
- [ ] Rollback image tag recorded before rc deploy  
- [ ] Pilot tenant list for golden matrix  

---

## 9. Related documents

- Merge order: [`BRANCH_STRATEGY.md`](./BRANCH_STRATEGY.md)  
- Hotfix source detail: [`branch-02-foundation-os-brain.md`](./branch-02-foundation-os-brain.md) § P0  
- Release: [`RELEASE_v1_0_0.md`](./RELEASE_v1_0_0.md)  

---

*Branch 00 is policy, not a long-lived git feature branch.*
