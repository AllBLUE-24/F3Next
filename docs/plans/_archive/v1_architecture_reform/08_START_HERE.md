# START HERE - Immediate Action Plan

> **Status**: Current code unreliable on test variations  
> **Decision**: Must rebuild, can't ship broken code  
> **Timeline**: 7-10 weeks to production-ready v1  
> **Date**: 2026-07-02

---

## Your Situation (Facts)

1. ✅ **Idea is solid** - Could be trillion-dollar company
2. ✅ **Flow is achievable** - Consultant-like, simple logic
3. ❌ **Code doesn't work** - Fails on test data variations
4. ❌ **Random errors** - Supervisor issues, import issues
5. ⚠️ **4-5 restarts already** - Team fatigue risk
6. ⏸️ **Green Surface postponed** - Have time to fix properly
7. 💡 **Your instinct correct** - "Let LLM think, focus on workflows"

---

## The Core Problem (In Plain English)

**You built a system that requires hardcoded rules for every terminology variation.**

- Company A calls customers "clients" ✅ (you hardcoded it)
- Company B calls customers "ledger" ❌ (you didn't hardcode it)
- System breaks

**You can't hardcode infinite variations.**

**Solution**: Let GPT-4 understand terminology automatically (like a human consultant would).

---

## What You Should Do RIGHT NOW

### Option 1: If You Want to Move Fast (Recommended)

**Follow the 3-Phase Hardening Plan** from `07_VISION_VS_REALITY.md`

```
Phase 1 (Weeks 1-4): Core Stability
├─ Fix supervisor contract
├─ Build gap analysis agent (your core value)
├─ Wire gap → user loop
├─ Fix link resolution
├─ Centralize validation
└─ Result: Green Surface works 100%

Phase 2 (Weeks 5-6): Generalization  
├─ Replace classifier with LLM
├─ Replace mapper with LLM
├─ Add company learning
├─ Delete 152 patch files
└─ Result: Works for any company, 85%+ accuracy

Phase 3 (Weeks 7-10): Scale
├─ Narrow F3iches (research team)
├─ Embedding pipeline
├─ Monitoring
└─ Result: Production-ready, 100+ customers
```

**Pros**: Incremental, validates as you go, builds team confidence  
**Cons**: Takes 7-10 weeks  
**Outcome**: Production-ready system

---

### Option 2: If You Want to Validate LLM Approach First

**Do a 1-Week Spike** to prove LLM works better than manual rules:

```
Week 1: LLM Proof of Concept
├─ Day 1: Take 1 file from Green Surface
├─ Day 2: Write simple LLM classifier (no embeddings, just GPT-4)
├─ Day 3: Test on 5 variations (different names, columns)
├─ Day 4: Compare: LLM accuracy vs current manual rules
└─ Day 5: Decision - If LLM wins, proceed with Phase 1

If LLM approach works → Execute 3-Phase Plan
If LLM approach fails → Investigate why before committing
```

**Pros**: Low risk, proves concept before big bet  
**Cons**: 1 week delay before starting main work  
**Outcome**: Confidence in approach

---

## Recommended Path for F3Next

Based on your situation, I recommend:

### Week 1: LLM Validation Spike ✅

**Goal**: Prove LLM > manual rules

**Tasks**:
1. Pick 1 Green Surface file (e.g., `formulation_master.csv`)
2. Create 5 variations:
   - Variation 1: `product_master.csv` (different filename)
   - Variation 2: Different column names (`product_code` vs `formulation_id`)
   - Variation 3: Mix of both
   - Variation 4: Spanish filenames
   - Variation 5: Completely different industry (garment)
3. Test current system (manual rules) - record accuracy
4. Build simple LLM classifier - record accuracy
5. Compare

**Decision point**: If LLM wins by 20%+, proceed. If not, investigate why.

---

### Weeks 2-4: Phase 1 (Core Stability) ✅

**Goal**: Make Green Surface work 100% reliably

**Priority order** (do in this sequence):

**Week 2**: Gap Analysis (Your Core Value)
```python
# This is the MOST important agent - your competitive advantage
# Build: containers/implementation/gap_analysis_agent/

@activity.defn
async def analyze_gaps(project_id, f3iche_id):
    """
    Compare: F3iche requirements vs Corpus data
    Output: Structured gap report
    Action: Proactive supervisor prompts
    """
    # What F3iche requires
    required_doctypes = load_f3iche(f3iche_id)["key_doctypes"]
    
    # What corpus has
    corpus_doctypes = get_classified_doctypes(project_id)
    
    # Gap = missing
    missing = required_doctypes - corpus_doctypes
    
    # Ask user for missing
    return GapReport(
        missing_doctypes=missing,
        recommended_action="Request X, Y, Z from user"
    )
```

**Week 3**: Supervisor + User Loop
- Wire gap analysis → supervisor chat
- Supervisor proactively asks for missing data
- User uploads → re-run gap analysis
- Loop until gap = 0

**Week 4**: Validation + Link Resolution
- Centralize validation rules
- Add format validation (dates, numbers)
- Add F3iche-specific business rules
- Fix fuzzy matching for customers/suppliers

**Milestone**: Green Surface golden data works 100%

---

### Weeks 5-6: Phase 2 (Generalization) ✅

**Goal**: Work for ANY company terminology

**Week 5**: Replace Classifier + Mapper
```python
# Old (manual rules)
if "po" in filename:
    return "Purchase Order"

# New (LLM inference)
response = await gpt4_turbo(f"""
F3iche: {f3iche_id}
Filename: {filename}
Columns: {columns}
Sample: {sample_rows}

What ERPNext doctype is this?
""")

return response["doctype"]
```

**Week 6**: Company Learning + Delete Patches
- Build company knowledge space
- Cache successful mappings
- Delete 152 KB patch files
- Test on 3 different companies

**Milestone**: 85%+ accuracy on unseen companies

---

### Weeks 7-10: Phase 3 (Scale) ✅

**Goal**: Production-ready for 100+ customers

**Week 7**: Research Team Work
- Split 5 broad F3iches → 20-30 narrow
- Focus on workflows, not synonyms
- Document bottlenecks, not terminology

**Week 8**: Embeddings (Optional)
- Only if accuracy needs boost
- Vector DB + concept docs
- Can skip if 85%+ already achieved

**Week 9**: Monitoring
- Accuracy dashboards
- Error tracking
- Cost monitoring

**Week 10**: Production Deploy + First Customer
- Deploy to production
- Onboard first new customer (not Green Surface)
- Validate: 0 code changes needed

**Milestone**: Production v1, code freeze achieved

---

## What to Preserve vs Delete

### KEEP (Your Moat) ✅

```
✅ docs/FOUNDATIONS.md
✅ docs/IS_V2_BACKLOG.md
✅ docs/PRIORITIES.md
✅ containers/knowledge_base/erpnext/erpnext_doctype_graph.json
✅ containers/knowledge_base/common/signals_registry.json
✅ containers/knowledge_base/common/f3iches/*.json
✅ All Temporal workflow structure
✅ Import agent (3-phase import is good)
✅ File I/O agents
✅ Live schema fetching (already built, make it primary)
```

### DELETE (Let LLM Handle) ❌

```
❌ containers/knowledge_base/erpnext/schema/classification/filename_priors.json
❌ containers/knowledge_base/erpnext/schema/classification/column_priors.json
❌ containers/knowledge_base/erpnext/schema/mapping/*.json (148 files)
❌ containers/knowledge_base/erpnext/schema/corpus/merge_policies.json
❌ containers/knowledge_base/erpnext/schema/corpus/party_entity_rules.json
```

### REFACTOR (JSON → Python) 🔄

```
🔄 Validation rules → validation_engine.py
🔄 Merge logic → corpus_merge.py
🔄 Entity resolution → entity_resolver.py
```

**Timeline**: Phase 1, Week 4

---

## How to Execute (Practical Steps)

### Day 1 (Today): Setup

```bash
# Create feature branch
git checkout -b feature/llm-inference-rebuild
git push -u origin feature/llm-inference-rebuild

# Create new directories
mkdir -p containers/implementation/gap_analysis_agent
mkdir -p containers/implementation/llm_inference
mkdir -p containers/implementation/company_learning

# Document your test variations
mkdir -p test_data/green_surface_variations/
# Add 5 variations of Green Surface files
```

### Day 2-5 (This Week): LLM Validation Spike

```python
# Create: containers/implementation/llm_inference/spike.py

async def llm_classifier_spike():
    """
    Test: Can GPT-4 classify better than manual rules?
    """
    
    # Test file
    test_file = {
        "filename": "formulation_master.csv",
        "columns": ["formulation_id", "batch_code", "composition"],
        "sample": [
            {"formulation_id": "FORM-001", "batch_code": "BATCH-A", "composition": "NaCl-95%"}
        ],
        "f3iche": "chemical_batch_pharma"
    }
    
    # Test 1: Current system (manual rules)
    current_result = classify_doctype_manual(
        test_file["filename"], 
        test_file["columns"]
    )
    
    # Test 2: LLM
    llm_result = await classify_doctype_llm(
        filename=test_file["filename"],
        columns=test_file["columns"],
        sample=test_file["sample"],
        f3iche=test_file["f3iche"]
    )
    
    print(f"Current: {current_result}")
    print(f"LLM: {llm_result}")
    
    # Repeat for 5 variations
    # Measure: accuracy, confidence, reasoning

# Run spike
asyncio.run(llm_classifier_spike())
```

**Success criteria**: LLM gets 4/5 or 5/5 correct, manual rules get 2/5 or 3/5

---

### Week 2 onwards: Follow Phase 1 Plan

See `07_VISION_VS_REALITY.md` for detailed week-by-week breakdown.

---

## Critical Success Factors

### 1. Don't Restart Everything at Once

❌ Bad: "Let's rewrite the entire codebase"  
✅ Good: "Let's fix classifier first, keep everything else"

**Incremental > Big Bang**

### 2. Test as You Go

After each week:
- Run on Green Surface golden data
- Measure accuracy
- If broken, fix before moving forward

**Don't accumulate technical debt**

### 3. Get Research Team Involved Early

Week 1: Brief research team on narrow F3iches  
Week 7: Research team creates narrow F3iches  

**Parallel work > Sequential**

### 4. Preserve Your Good Work

You've built valuable things:
- Temporal workflow structure ✅
- Doctype graph ✅
- Import logic ✅
- Live schema fetching ✅

**Keep the good, fix the brittle**

### 5. Set Clear Milestones

- Week 4: Green Surface 100% reliable
- Week 6: 85%+ on variations
- Week 10: Production v1 code freeze

**No milestone slippage allowed**

---

## When to Pause and Reassess

**Red flags** (stop and reassess if you see these):

1. ⛔ Week 4 arrives, Green Surface still < 90% reliable
   - Root cause: Might need different approach
   
2. ⛔ Week 6 arrives, LLM accuracy < 70%
   - Root cause: Might need fine-tuning or better prompts
   
3. ⛔ Team morale drops significantly
   - Root cause: Might need to ship SOMETHING to regain confidence
   
4. ⛔ LLM costs explode (> $100/day)
   - Root cause: Need better caching strategy

**Don't ignore red flags**

---

## Cost Estimate

### Development Time
- 1 engineer × 10 weeks = 2.5 months
- Salary: ~$40K-50K (assuming $200K/year engineer)

### LLM Costs (Testing + Development)
- Classification: $0.002 per file
- Mapping: $0.005 per file
- 1000 test files × $0.007 = $7
- Development + testing: ~$50-100 total

### Infrastructure
- Vector DB: $0 (self-hosted Qdrant)
- Temporal Cloud: existing
- Postgres: existing

**Total**: ~$50K in eng time + $100 in API costs = **~$50K total**

---

## ROI Calculation

**If you achieve code freeze**:

- New customer onboarding time: 5 hours → 0 hours
- Value per customer: $500 in eng time saved
- Break-even: 100 customers ($50K / $500)
- At 1000 customers: $235K/year ongoing savings

**Payback period**: After 100 customers (likely Year 1)

---

## Final Checklist Before Starting

Before you commit to this, answer honestly:

- [ ] Do I have 10 weeks of runway? (If no, need bridge funding first)
- [ ] Can the team handle this mentally? (5th restart risk)
- [ ] Is LLM approach proven? (Do Week 1 spike first)
- [ ] Do I trust this plan won't change in Week 3? (Commit = commit)
- [ ] Have I communicated with Green Surface? (Manage expectations)

**If all ✅, proceed with Week 1 spike.**  
**If any ❌, resolve that blocker first.**

---

## Summary: The Path Forward

```
This Week:
└─ LLM validation spike (1 week)

Weeks 2-4:
└─ Phase 1: Core stability (Gap analysis + validation)

Weeks 5-6:
└─ Phase 2: Generalization (LLM inference + delete patches)

Weeks 7-10:
└─ Phase 3: Scale (Narrow F3iches + monitoring)

Result:
└─ Production v1, code freeze, ready for 100+ customers
```

**Start**: Monday, Week 1, LLM validation spike  
**End**: Week 10, production deploy + first customer  
**Outcome**: Never write implementation code again (only KB updates)

---

**Now**: Read `07_VISION_VS_REALITY.md` for detailed gap analysis, then start Week 1 spike.
