# V1 Architecture Reform Documentation

> **Created**: 2026-07-01  
> **Status**: Proposed - Pending CEO Decision  
> **Context**: Pre-seed stage, seeking first customer + VC funding

---

## What This Is

Complete documentation of the proposed architectural reform for F3Next Implementation System, addressing the KB file sprawl and scaling limitations of the current patch-driven approach.

---

## Documents Overview

| # | Document | Purpose | Read Time | Audience |
|---|----------|---------|-----------|----------|
| 00 | [Overview](00_OVERVIEW.md) | Executive summary + quick decision guide | 5 min | Everyone |
| 01 | [Current State Audit](01_CURRENT_STATE_AUDIT.md) | What's broken and why | 15 min | All |
| 02 | [Proposed Architecture](02_PROPOSED_ARCHITECTURE.md) | How to fix it (technical deep-dive) | 30 min | Tech + Research |
| 03 | [KB Structure](03_KB_STRUCTURE.md) | File organization and ownership | 20 min | Research Team |
| 04 | [Implementation Plan](04_IMPLEMENTATION_PLAN.md) | Week-by-week execution roadmap | 25 min | Tech Team |
| 05 | [Onboarding Matrices](05_ONBOARDING_MATRICES.md) | What changes when (customer, F3iche, ERP) | 15 min | Product |
| 06 | [Decision Framework](06_DECISION_FRAMEWORK.md) | Ship now vs rebuild analysis | 20 min | CEO |
| 07 | [Vision vs Reality](07_VISION_VS_REALITY.md) | Gap analysis + 3-phase hardening plan | 20 min | CTO + Tech |
| 08 | [START HERE](08_START_HERE.md) | ⚡ Immediate action plan (READ THIS FIRST) | 15 min | Everyone |
| 09 | [Core KB & Stepwise Migration](09_CORE_KB_AND_STEPWISE_MIGRATION.md) | 🛠️ Execution doctrine: core KB allowlist, no-delete-first steps, agent guide | 20 min | Coding agents + Tech |
| 10 | [MVP Boundary V1 Plan](10_MVP_BOUNDARY_V1_PLAN.md) | 🚧 **Active gate:** archetype-driven scoping, harness golden tests, no new patches | 25 min | Engineering |

**Total read time**: ~3.5 hours for complete understanding

---

## Quick Start

### ⚡ If Discovery MVP Boundary Is Broken (Active — July 2026)

Read: [10_MVP_BOUNDARY_V1_PLAN.md](10_MVP_BOUNDARY_V1_PLAN.md) — **Gate before Discovery step is v1-worthy**

Covers: harness failures, archetype registry, Phase 0–6 engineering tasks, golden 10/10 gate.

---

### ⚡ If You Are Executing KB Reform Step-by-Step

Read: [09_CORE_KB_AND_STEPWISE_MIGRATION.md](09_CORE_KB_AND_STEPWISE_MIGRATION.md) — **Start here for coding agents**

Covers: core KB allowlist, patch→prompt philosophy, Steps 0–8 with 10/10 gates, no-delete-first rule.

---

### ⚡ If You Need to Act NOW (Current Code Broken)

Read: [08_START_HERE.md](08_START_HERE.md) - **Start with this if code doesn't work reliably**

Then: Execute Week 1 LLM validation spike

---

### If You Have 5 Minutes

Read: [00_OVERVIEW.md](00_OVERVIEW.md) + [06_DECISION_FRAMEWORK.md](06_DECISION_FRAMEWORK.md)

**Key decision**: Ship current code NOW or rebuild foundation (2-3 months)?

---

### If You Have 30 Minutes

Read in order:
1. [08_START_HERE.md](08_START_HERE.md) - Immediate action plan
2. [07_VISION_VS_REALITY.md](07_VISION_VS_REALITY.md) - Your flow vs actual gaps
3. [06_DECISION_FRAMEWORK.md](06_DECISION_FRAMEWORK.md) - Decision

---

### If You Have 2 Hours (Full Context)

Read all 9 documents in order:
1. Start with [08_START_HERE.md](08_START_HERE.md)
2. Then read 00-07 in numerical order

---

## Key Findings

### The Core Problem

**152 KB patch files** created to fix one-off issues. Current system:
- Requires 5-6 hours of patching per new customer
- Requires 4-5 hours per new doctype
- Does NOT scale beyond 10-20 customers
- Blocks research team (tech team doing their work)

### The Proposed Solution

**Multi-layer knowledge architecture**:
1. **Narrow F3iches** (50-100 specific, not 5 broad)
2. **Company-specific learning** (learn from uploads)
3. **Live ERP schema** (already built, make it primary)
4. **LLM inference** (replaces manual rules)

**Result**: New customer = 0 changes (fully automatic)

### The Cost

**Time**: 8-10 weeks (2-3 months)  
**Engineering**: 1-2 senior engineers  
**Risk**: High (5th restart), but foundation is correct  

### The ROI

**Break-even**: 100 customers  
**Annual savings at 1000 customers**: $235K  
**Scale limit**: Unlimited (vs 10-20 with current)

---

## Decision Factors

### Ship Current Code Now If:
- ✅ Green Surface ready to sign this month
- ✅ Runway < 6 months
- ✅ Need revenue for next fundraise
- ✅ Team has low morale (restart fatigue)

### Rebuild Foundation If:
- ✅ Runway > 12 months
- ✅ No immediate customer pipeline
- ✅ Confident architecture is blocking sales
- ✅ Team has energy for proper rebuild

### Hybrid Approach (Recommended) If:
- ✅ Runway 6-12 months
- ✅ Green Surface interested but not urgent
- ✅ Want validation before big architectural bet
- ✅ Team has 2+ engineers

---

## Recommendation

> **Ship to Green Surface first (2 weeks) → Validate → Then decide on rebuild**

**Why**: Pre-seed companies die from lack of customers, not messy code. Get ONE paying customer, collect real pain points, THEN make the rebuild decision based on data (not theory).

See [06_DECISION_FRAMEWORK.md](06_DECISION_FRAMEWORK.md) for full analysis.

---

## What Happens Next

### Option 1: Decision = Ship Now

**Actions**:
1. Fix 2-3 critical bugs (see production blockers)
2. Deploy to Green Surface staging
3. Get contract signed (even $1/month)
4. Monitor usage for 4 weeks
5. Decide: Rebuild vs Keep Patching vs Pivot

### Option 2: Decision = Rebuild Now

**Actions**:
1. Get team buy-in (this is the LAST restart)
2. Follow [04_IMPLEMENTATION_PLAN.md](04_IMPLEMENTATION_PLAN.md) week-by-week
3. Set up weekly checkpoints
4. Week 8: Production deploy
5. Week 10: First customer onboarding

### Option 3: Decision = Hybrid

**Actions**:
1. Week 1-2: Ship current code to Green Surface
2. Week 3-6: Support + collect pain points
3. Week 7-14: Rebuild in parallel
4. Week 15: Migrate customer 1 to new system
5. Week 16+: Customers 2-5 on new architecture

---

## Critical Questions to Answer

Before making decision, answer these:

1. **Can you close Green Surface this month?** (If no, why?)
2. **How much runway do you have?** (Critical factor)
3. **Why haven't you shipped to anyone yet?** (Architecture or other?)
4. **Can the team handle 1 more rebuild?** (Honest assessment)
5. **What's blocking customer acquisition RIGHT NOW?** (Product, sales, positioning?)

---

## Files to Review Based on Role

### CEO / Founder
1. [00_OVERVIEW.md](00_OVERVIEW.md) - Big picture
2. [06_DECISION_FRAMEWORK.md](06_DECISION_FRAMEWORK.md) - Decision analysis
3. [05_ONBOARDING_MATRICES.md](05_ONBOARDING_MATRICES.md) - Scaling economics

### CTO / Tech Lead
1. **[08_START_HERE.md](08_START_HERE.md)** - ⚡ Read this first
2. [07_VISION_VS_REALITY.md](07_VISION_VS_REALITY.md) - Gap analysis + 3-phase plan
3. [01_CURRENT_STATE_AUDIT.md](01_CURRENT_STATE_AUDIT.md) - What's broken
4. [02_PROPOSED_ARCHITECTURE.md](02_PROPOSED_ARCHITECTURE.md) - How to fix
5. [04_IMPLEMENTATION_PLAN.md](04_IMPLEMENTATION_PLAN.md) - Execution plan

### Research Team Lead
1. [03_KB_STRUCTURE.md](03_KB_STRUCTURE.md) - File ownership
2. [05_ONBOARDING_MATRICES.md](05_ONBOARDING_MATRICES.md) - What changes when
3. [02_PROPOSED_ARCHITECTURE.md](02_PROPOSED_ARCHITECTURE.md) - Layer 0 (F3iches)

### Product Manager
1. [05_ONBOARDING_MATRICES.md](05_ONBOARDING_MATRICES.md) - Customer onboarding
2. [06_DECISION_FRAMEWORK.md](06_DECISION_FRAMEWORK.md) - Timeline implications
3. [00_OVERVIEW.md](00_OVERVIEW.md) - Success criteria

---

## Success Metrics

**If we rebuild, we must achieve**:

1. ✅ New customer onboarding = **0 code changes**
2. ✅ New customer onboarding = **0 KB file changes**
3. ✅ Mapping accuracy = **90%+ on first upload**
4. ✅ Mapping accuracy = **95%+ after 3 uploads**
5. ✅ Classification accuracy = **90%+**
6. ✅ Research team autonomous (not blocked on tech)

**Timeline**: 8-10 weeks (no exceptions)

---

## Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| **Restart fatigue** (5th time) | HIGH | Ship first, then rebuild |
| **Runway burn** (2-3 months) | HIGH | Only rebuild if > 6 months runway |
| **Unproven architecture** | MEDIUM | Validate with customer first |
| **Team split** (hybrid) | MEDIUM | Clear ownership, weekly sync |
| **Green Surface churns** | HIGH | If so, architecture wasn't blocker |

---

## Related Documentation

- [../FOUNDATIONS.md](../FOUNDATIONS.md) - L0-L5 layer model (still valid)
- [../IS_V2_BACKLOG.md](../IS_V2_BACKLOG.md) - Implementation pillars (still valid)
- [../PRIORITIES.md](../PRIORITIES.md) - Current sprint focus
- [../NORTH_STAR.md](../NORTH_STAR.md) - Product vision

**Note**: This reform does NOT invalidate existing docs - it builds on the L0-L5 foundation with better implementation.

---

## Contact & Questions

**For questions on**:
- Decision framework → CEO
- Technical architecture → CTO
- KB structure → Research Team Lead
- Implementation timeline → Tech Team Lead

---

## Next Steps

1. **CEO reads**: [06_DECISION_FRAMEWORK.md](06_DECISION_FRAMEWORK.md)
2. **Team meeting**: Discuss options (ship vs rebuild vs hybrid)
3. **Decision deadline**: Within 3 days
4. **Execution starts**: Immediately after decision

**Do NOT delay decision more than 1 week. Every week of indecision = 1 week of runway burned.**

---

## Version History

| Date | Version | Changes |
|------|---------|---------|
| 2026-07-01 | 1.0 | Initial documentation package created |

---

**Status**: ⏳ Awaiting CEO decision

**Prepared by**: Technical Leadership  
**Review date**: 2026-07-01  
**Decision deadline**: 2026-07-05 (recommended)
