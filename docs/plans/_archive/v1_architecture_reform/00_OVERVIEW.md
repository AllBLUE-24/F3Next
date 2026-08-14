# V1 Architecture Reform - Overview

> **Date**: 2026-07-01  
> **Status**: Proposed - Pending Decision  
> **Context**: Pre-seed stage, zero customers, seeking first customer + VC funding

---

## Executive Summary

After thorough analysis of the implementation system, we identified **critical architectural flaws** that block production readiness and customer acquisition:

1. **KB File Sprawl**: 150+ JSON patch files created to fix one-off issues
2. **Synonym Hell**: Manual synonym lists that don't scale beyond 15-20 doctypes
3. **No Learning System**: Every new customer requires file changes
4. **Blurred Responsibilities**: Tech team doing research work, research team blocked

**Proposed Solution**: Multi-layer knowledge architecture with narrow F3iches and company-specific learning.

**Decision Required**: Ship current messy code fast OR rebuild foundation properly (2-3 month delay).

---

## Document Structure

This reform package contains:

| Doc | Purpose | Audience |
|-----|---------|----------|
| `00_OVERVIEW.md` | Executive summary (this doc) | CEO, Board |
| `01_CURRENT_STATE_AUDIT.md` | What's broken and why | All |
| `02_PROPOSED_ARCHITECTURE.md` | How to fix it | Tech + Research |
| `03_KB_STRUCTURE.md` | File organization and ownership | Research Team |
| `04_IMPLEMENTATION_PLAN.md` | Step-by-step execution | Tech Team |
| `05_ONBOARDING_MATRICES.md` | What changes when (customer, F3iche, ERP) | Product |
| `06_DECISION_FRAMEWORK.md` | Ship now vs rebuild analysis | CEO |

---

## Key Questions Answered

### Q: Why is current architecture broken?

**A**: 150+ JSON files created as patches for individual customer issues. Doesn't scale.

### Q: Can we scale with current approach?

**A**: No. Manual synonyms work for 15 doctypes, fail at 50+, impossible at 800.

### Q: What's the core unsolved problem?

**A**: **Infinite terminology variations across companies**. No amount of manual synonym files will cover it.

### Q: What's the right solution?

**A**: Three-layer approach:
1. **Narrow F3iches** (50-100 specific business types, not 5 broad ones)
2. **Company-Specific Learning** (learn from customer's own data)
3. **Fine-Tuning** (after 100 customers, optional)

### Q: Do we need to restart from scratch?

**A**: **No.** Current code works for Green Surface. Ship to first customer, then refactor incrementally.

### Q: What if we restart anyway?

**A**: 2-3 month delay. Risky for pre-seed. But if foundation is truly blocking sales, might be necessary.

---

## Recommendation Matrix

| Scenario | Recommendation | Rationale |
|----------|---------------|-----------|
| **Green Surface ready to buy** | Ship current code | Revenue > perfection |
| **No customers in pipeline** | Consider rebuild | Have time to fix foundation |
| **VC pitch in 2 weeks** | Ship current code | Need working demo |
| **VC pitch in 3 months** | Rebuild foundation | Can show progress + vision |
| **Competitor launching soon** | Ship current code | Speed to market critical |
| **Team morale low (4-5 restarts)** | Ship current code | Confidence from shipping |

---

## Success Criteria (If Rebuilding)

**Must achieve before considering success:**

1. ✅ New customer onboarding = **0 code changes, 0 KB file changes**
2. ✅ New F3iche = **1 JSON + 2-3 docs only**
3. ✅ New doctype = **1 line in graph only**
4. ✅ Accuracy = **90%+ on unmapped columns**
5. ✅ Research team autonomous (not blocked on tech)

**Timeline**: 2-3 months full-time if rebuilding properly.

---

## Risk Assessment

### If We Ship Current Code (Messy but Works)

**Pros**:
- Customer revenue this month
- Validation of product-market fit
- Real data to guide architecture decisions
- Team momentum (shipping = confidence)

**Cons**:
- Technical debt accumulates
- Hard to maintain as customers grow
- May need emergency refactor at 10-20 customers

**Severity**: Medium risk

---

### If We Rebuild Foundation

**Pros**:
- Correct architecture from start
- Scalable to 100+ customers
- Research team autonomous
- Clean codebase attracts talent

**Cons**:
- 2-3 month delay to first customer
- Unproven architecture (no customer data)
- Runway burn (if pre-seed funds limited)
- Team fatigue (5th restart)

**Severity**: High risk for pre-seed

---

## Next Steps

1. **CEO Decision**: Ship now OR rebuild (see `06_DECISION_FRAMEWORK.md`)
2. **If Ship**: Read `01_CURRENT_STATE_AUDIT.md` to know what to fix incrementally
3. **If Rebuild**: Follow `04_IMPLEMENTATION_PLAN.md` week-by-week
4. **Share with Team**: Align on direction before starting

---

## Related Docs

- Current architecture: `../ARCH_IMPLEMENTATION.md`
- Current backlog: `../IS_V2_BACKLOG.md`
- Current priorities: `../PRIORITIES.md`
- Foundations model: `../FOUNDATIONS.md`

This reform does NOT invalidate those docs - it builds on top of the L0-L5 layer model.

---

**Author**: Technical Leadership  
**Review Date**: 2026-07-01  
**Next Review**: After first customer ships OR after rebuild complete
