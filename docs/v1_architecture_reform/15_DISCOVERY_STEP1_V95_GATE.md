# Discovery Step 1 — v1-worthy 9.5+ gate

> **Created**: 2026-07-24  
> **Status**: Active  
> **Parent**: [`14_DISCOVERY_STEP1_CONSULTATIVE_PLAN.md`](./14_DISCOVERY_STEP1_CONSULTATIVE_PLAN.md)

---

## Exit bar

Step 1 ships when **any** discovery transcript produces a Day-1 contract a senior consultant would sign — without niche/company hardcoding.

| Rating | Meaning |
|--------|---------|
| **9.5+** | GREEN assurance, closure test matches bottleneck, explainer aligns with clarifications, golden matrix ≥80% live |
| **RED** | Block confirm until replan |
| **YELLOW** | Show assumptions; user acknowledges before confirm |

---

## Sprint (structural only)

1. **Clarification → validator policy** (`discovery_clarification_policy.py`) — MTS/MTO, trace, routing, QC
2. **Batch/lot closure signal** — manufacturing + batch language → `Batch` Day-1
3. **Grounded workflow explainer** — validated plan + clarifications as hard context
4. **Assurance tightening** — GREEN requires closure test, no warnings, ≤2 promotions
5. **Golden + policy tests** — offline + live matrix gate

---

## Verification

```powershell
pytest containers/discovery/test/test_clarification_policy.py containers/discovery/test/test_discovery_assurance.py -q
pytest containers/discovery/test/test_planner_v1_worthiness.py -q
python -m containers.discovery.test.harness_mvp_boundary --planner-offline --report
```

Live matrix ≥80% remains the final gate before Step 2 upload.
