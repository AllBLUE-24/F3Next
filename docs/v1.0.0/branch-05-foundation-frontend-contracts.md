# Branch 05 — `foundation/frontend-contracts`

> **Base:** `foundation/kb-validation`  
> **Layer focus:** L1, L5  
> **Class:** **A** (UI lies), **C** (gate result UI)

---

## 1. Branch thesis

Users judge F3Next by **what the UI says**. This branch aligns frontend types, states, and copy to **GateResult** honesty — no green completion on partial backend failure, clear CLARIFY prompts with candidates, OS confirm that actually reaches Temporal.

Backend gates must exist before this branch (os-brain + is-brain + kb).

---

## 2. Surfaces in scope

| Surface | Repo area (typical) |
|---------|---------------------|
| IS upload / validate / import | `frontend/` implementation routes |
| IS supervisor / chat bar | session components |
| OS command terminal | OS pipeline UI |
| OS clarification / confirm | modal or inline forms |
| Shared API client | fetch wrappers, error handling |

*Exact paths: grep `steps_failed`, `import-results`, `os/confirm` in frontend during implementation.*

---

## 3. API contracts (target)

### 3.1 IS session status

| Backend `stage` / `status` | UI must show |
|----------------------------|--------------|
| `validating` | In progress |
| `validated` + `valid=false` | Fail or partial — list errors |
| `importing` | Phase label from API |
| `complete` + `steps_failed > 0` | **Partial success** — never badge “Complete” |
| `complete_with_errors` | Explicit partial state |

**Source of truth:** `GET /api/implementation/import-results/{project_id}`

### 3.2 OS command session

| Field | UI use |
|-------|--------|
| `pipeline_step` | Progress indicator |
| `awaiting_clarification` | Show questions + candidates |
| `resolution_gaps[]` | Render choice buttons from `candidates` |
| `semantic_confirm_required` | Block execute until confirm |
| `execute_result.success` | Terminal message |

### 3.3 Confirm endpoint

| Requirement | Detail |
|-------------|--------|
| `POST /api/os/confirm/{workflowId}` | Retry + visible error if fetch fails |
| Timeout policy | If backend auto-proceeds at 5 min, show countdown + “Confirm now” |
| Loading state | Disable double-submit |

---

## 4. Component-level ideation

### 4.1 Validate panel (IS)

- **Pass / partial / fail** badges with counts  
- Expandable row errors linked to `rule_id` (tooltip: remediation from KB)  
- Disable “Start import” on `fail` unless product policy allows partial import with acknowledgement  

### 4.2 Import results panel (IS)

- Per-doctype table: success / failed / skipped  
- Link to ERP doc when `name` returned  
- Aggregate: “12 of 15 succeeded” — matches API `steps_failed`  

### 4.3 Supervisor / CLARIFY (IS)

- Question text from `GapItem.question`  
- **Choice** gaps: radio list from `candidates` (live ERP names)  
- **Blocking** gaps: free text only when no candidates  
- Re-upload dropzone when gap type = `file_missing`  

### 4.4 OS terminal

- Step list mirrors workflow: RESOLVE → COMPLETE → CLARIFY → COMMIT  
- On LER miss: “I couldn’t find customer X in your ERP. Did you mean: …”  
- On execute failure: plain `format_result` message, not stack trace  

### 4.5 OS clarification form

- Preserve context: show locked customer/supplier when only delivery asked  
- Skip chip: “Not needed” sends skip phrase to backend  
- Do not render inputs for autofill fields (hide `title`, `naming_series`)  

### 4.6 OS confirm modal

- Semantic warnings as **advisory** (yellow), hard preflight as **blocking** (red)  
- Confirm button calls API; show failure reason from network layer  

---

## 5. TypeScript types (suggested)

**File:** `frontend/src/types/gates.ts`

```typescript
export type GateName = 'resolve' | 'complete' | 'clarify' | 'commit';
export type GateStatus = 'ok' | 'needs_human' | 'blocked';

export interface GapItem {
  field: string;
  question: string;
  candidates?: string[];
  severity: 'blocking' | 'choice' | 'hint';
  rule_id?: string;
}

export interface GateResult {
  gate: GateName;
  status: GateStatus;
  gaps: GapItem[];
  honesty?: {
    valid: boolean;
    errors: string[];
    warnings: string[];
  };
}
```

Map from API responses in adapters — version field `brain_version` optional display in debug panel.

---

## 6. UX copy principles

| Bad | Good |
|-----|------|
| `MandatoryError: title` | “We’ll set the order title automatically.” |
| `unknown_customer` | “Customer ‘X’ isn’t in ERP yet. Pick one or add in ERP.” |
| `Failed to fetch` | “Couldn’t reach the server. Check connection and retry Confirm.” |
| Green check on partial import | “Imported 12 of 15 — 3 failed. See details below.” |

Align with [`OPERATING_MODEL.md`](./OPERATING_MODEL.md) § User experience.

---

## 7. Accessibility & responsive

- Choice lists keyboard navigable  
- Touch targets for confirm / skip on mobile (future mic uses same components)  
- Error text not color-only  

Use project design skills only if UI redesign requested; default = contract alignment minimal diff.

---

## 8. Verification

| Test | Type |
|------|------|
| Import UI with mocked `steps_failed=1` | Component test — no “Complete” |
| Confirm fetch failure | Network mock — error visible |
| Clarification candidates | Snapshot test |
| E2E (optional) | Playwright against staging |

Manual: full Regww PO flow including confirm click.

---

## 9. PR breakdown

1. Type definitions + API mappers  
2. IS validate/import honesty  
3. IS supervisor candidates  
4. OS terminal + clarification  
5. OS confirm reliability  
6. Copy pass for top 20 error codes  

---

## 10. Non-goals

- Full visual redesign / design system extraction  
- Mic / voice UI  
- New backend endpoints (consume existing)

---

## 11. Success criteria

- [x] RELEASE checklist P5, H1–H3, H4 documented in UI (honesty labels, partial import, validate fail gate)  
- [ ] G-OS-SO-03 confirm path manual pass ([`FOUNDATION_VERIFICATION.md`](./FOUNDATION_VERIFICATION.md))  
- [x] Zero false-green import in QA script (vitest `import-results.test.ts`)  
- [ ] Ready for `v1.0.0-rc` tag — run manual golden + worker rebuild  

---

*Program complete → [`RELEASE_v1_0_0.md`](./RELEASE_v1_0_0.md)*
