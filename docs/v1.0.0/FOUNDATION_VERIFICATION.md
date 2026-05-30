# v1.0.0 Foundation Verification

> **Automated:** `python scripts/verify_foundation.py`  
> **Manual golden:** this checklist before tagging `v1.0.0-rc`

---

## 1. Automated regression (must pass)

| Step | Command | Covers |
|------|---------|--------|
| Full foundation | `python scripts/verify_foundation.py` | All rows below |
| Shared + OS | `pytest shared/tests containers/os/tests -q` | P1–P2, B*, E* unit anchors |
| IS brain | `pytest containers/implementation/tests/test_ler_validate.py containers/implementation/tests/test_live_erp_readiness.py -q` | G-IS-LER-01, G-IS-READ-01 |
| KB sync | `python scripts/sync_autofill_from_kb.py --check` | Branch 04 autofill parity |
| L0 smoke | `python -m shared.smoke_llm` | P7 (if LLM env configured) |
| Frontend | `cd frontend && npm run test && npm run build` | P5, G-IS-IMP-01 logic |

**Worker deploy (P6 — not automated):**

```bash
docker compose build os_worker implementation_worker
docker compose up -d os_worker implementation_worker
```

---

## 2. Golden matrix — manual E2E

Mark each row after a live run on staging/pilot tenant.

### OS — Strahats / any pilot

| ID | Pass? | Notes |
|----|-------|-------|
| G-OS-SO-01 | ☐ | SO after UI-created customer; LER finds live name |
| G-OS-SO-02 | ☐ | Delivery date clarification preserves party |
| G-OS-SO-03 | ☐ | Confirm button → `POST /api/os/confirm/{id}`; countdown visible |
| G-OS-SO-04 | ☐ | Unknown customer → clarification, not silent high confidence |

### OS — Regww / purchase

| ID | Pass? | Notes |
|----|-------|-------|
| G-OS-CO-01 | ☐ | Company = live ERP name (unit: `test_validator_company_guard`) |
| G-OS-PO-01 | ☐ | Title autofill; no title prompt (unit: `test_business_fields`) |
| G-OS-PO-02 | ☐ | Subcontract preflight before POST (unit: `test_kb_policy`) |

### OS — cross-cutting

| ID | Pass? | Notes |
|----|-------|-------|
| G-OS-VAL-01 | ☐ | Validation repair loop; no workflow crash |
| G-OS-MERGE-01 | ☐ | Clarification merge preserves supplier/customer |

### IS — Green Surface

| ID | Pass? | Notes |
|----|-------|-------|
| G-IS-VAL-01 | ☐ | Validate pass/partial/fail honest; fail blocks import |
| G-IS-IMP-01 | ☐ | Partial import UI when steps failed (vitest + live) |
| G-IS-LER-01 | ☐ | Warehouse alias rewrite before POST |
| G-IS-READ-01 | ☐ | Greenfield: empty live master OK when files cover it |

### Freshness

| ID | Pass? | Notes |
|----|-------|-------|
| G-FRESH-01 | ☐ | Webhook → CVS; next OS command still uses LER |
| G-FRESH-02 | ☐ | Post-import CVS sync (step 13.5 or manual force-sync) |

---

## 3. Release checklist mapping

| RELEASE § | Automated | Manual |
|-----------|-----------|--------|
| P1–P5 code merged | Git / PR | Merge to `main` |
| P6 workers | — | Docker rebuild |
| P7 L0 smoke | `verify_foundation.py` | API keys in env |
| H1–H4 honesty | Unit + vitest | Validate/import UI walkthrough |
| B1–B4 LER | Unit tests | G-OS-SO-01, G-OS-SO-04 |
| E1–E3 execution | `test_kb_policy`, `test_submit_gate` | G-OS-PO-02 live |

---

## 4. Known acceptable failures (v1.0.0)

See [`RELEASE_v1_0_0.md`](./RELEASE_v1_0_0.md) §7 — document in beta report, do not hide in UI.

| Failure | Class | Action |
|---------|-------|--------|
| CVS step 13.5 force-sync | D | Manual `/api/cvs/force-sync/{project_id}` |
| Work Order when BOM not submitted | A | Fixed via submit_gate; re-run phase C |
| BOM list `disabled` 417 | D | Adapter warning only |

---

## 5. Sign-off gate for `v1.0.0-rc`

- [ ] `python scripts/verify_foundation.py` exit 0  
- [ ] Workers rebuilt on staging  
- [ ] Green Surface golden re-run **or** classified beta report (pass + ≤5 known failures)  
- [ ] Manual rows G-OS-SO-03 and G-IS-IMP-01 checked on live UI  
- [ ] `RELEASE_v1_0_0.md` §8 sign-off table filled  

---

*Last updated: foundation program closure*
