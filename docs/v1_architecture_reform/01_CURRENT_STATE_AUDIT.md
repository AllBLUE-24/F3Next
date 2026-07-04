# Current State Audit - What's Broken

> **Severity**: CRITICAL  
> **Impact**: Blocks production scale (can support 1-5 customers, breaks at 10+)

---

## KB File Inventory

### Research Team Files (LEGITIMATE) ✅

| File | Lines | Owner | Status |
|------|-------|-------|--------|
| `erpnext_doctype_graph.json` | 755 | Research | ✅ Excellent |
| `signals_registry.json` | ~500 | Research | ✅ Good structure |
| F3iche definitions (4 files) | ~200 each | Research | ⚠️ Too broad |
| Embedding corpus | N/A | Research | ❌ Doesn't exist yet |

**Total: ~6 core files** - This is CORRECT scale.

---

### Tech Team Patch Files (PROBLEMATIC) ❌

| File Pattern | Count | What It Contains | Why It's Wrong |
|-------------|-------|------------------|----------------|
| `mapping/*.json` | 148 | Field schemas + manual synonyms per doctype | 90% redundant with live Frappe API |
| `filename_priors.json` | 1 (230 lines) | Weighted keywords: "po" → Purchase Order | LLM can infer this |
| `column_priors.json` | 1 (17 lines) | Column hints: "project_name" → Project | LLM can infer this |
| `merge_policies.json` | 1 | Dedupe keys, quarantine rules | Business logic in JSON (should be code) |
| `party_entity_rules.json` | 1 | Entity resolution patches | Business logic in JSON (should be code) |
| `global_hints.json` | 1 | Classification patches | More manual rules that don't scale |

**Total: 152 patch files** - This is INSANE scale.

---

## Example: Customer.json Analysis

**File size**: 615 lines  
**What it contains**:

```json
{
  "customer_name": {
    "fieldname": "customer_name",      // ← Live Frappe API has this
    "fieldtype": "Data",               // ← Live Frappe API has this
    "mandatory": true,                 // ← Live Frappe API has this
    "user_input_synonyms": [           // ← ONLY unique part (manual patch)
      "customer", "client_name", "buyer_name", "party_name",
      "ledger_name", "Ledger_Name"
    ]
  }
  // ... 50 more fields, same pattern
}
```

**Problem**: 
- 90% of this file = duplicate of Frappe `GET /api/resource/DocType/Customer`
- 10% = manual synonyms that won't cover all companies
- Company A calls customers "ledger_name" ✅ (we listed it)
- Company B calls customers "account_master" ❌ (we didn't list it)
- Company C calls customers "party_code" ❌ (we didn't list it)

**Conclusion**: Doesn't scale. Needs rewrite.

---

## Code Dependencies Audit

### What Code Currently Reads

```python
# containers/implementation/mapping_agent/classifier.py
def classify_doctype(filename, columns):
    # Reads filename_priors.json
    filename_scores = _filename_priors(filename, candidates)
    # Reads column_priors.json  
    column_scores = _column_priors(columns, candidates)
    # Hardcoded weighted scoring
    return best_match

# containers/implementation/mapping_agent/kb.py
def field_mappings():
    # Loads ALL 148 mapping/*.json files
    # Returns massive dict with manual synonyms
    return composed_mappings

# containers/implementation/mapping_agent/corpus_merge.py  
def merge_extracted_rows(doctype, rows):
    # Reads merge_policies.json
    dedupe_key = policies["dedupe_key"][doctype]
    # Hardcoded merge logic
```

**Problem**: Every new doctype needs:
1. Entry in `filename_priors.json`
2. Entry in `column_priors.json`
3. New file in `mapping/NewDoctype.json` with manual synonyms
4. Entry in `merge_policies.json`

**Time per doctype**: 2-3 hours of manual work  
**Scale limit**: ~50 doctypes before team gives up

---

## Live Schema Fallback (ALREADY BUILT, UNDERUTILIZED)

**Great news**: You already built live schema fallback!

```python
# containers/implementation/mapping_agent/live_schema.py (207 lines)
async def fetch_live_doctype_schema(doctype, project_id):
    """
    Fetches schema from customer's ERPNext via Frappe REST API.
    Returns: [{"fieldname": str, "fieldtype": str, "mandatory": bool, ...}]
    Auto-generates basic synonyms from fieldname + label.
    """
    
# shared/erp_adapters/erpnext.py line 831
async def get_doctype_schema(self, doctype: str):
    """GET /api/resource/DocType/{doctype}"""
```

**Current usage**: Fallback when mapping/*.json doesn't have doctype  
**Should be**: PRIMARY source, not fallback

**Why it solves the problem**:
- Customer's ERPNext has ACTUAL field structure
- No need to manually write 148 files
- Works for ANY doctype, even custom ones
- Auto-generates basic synonyms

---

## The Core Unsolved Problem

### Terminology Explosion

**Company A** (Garment Export):
```csv
style_code, buyer_name, po_ref, color_name, size_code
STYLE-001, H&M, PO-2024-01, Navy, L
```

**Company B** (Chemical Batch):
```csv
formulation_id, distributor, batch_ref, composition, lot_size
FORM-A01, ChemCo, BATCH-2024-01, NaCl-95%, 500kg
```

**Company C** (Job Shop):
```csv
part_number, client_code, wo_ref, material_spec, qty
PART-1234, CLI-01, WO-2024-01, SS304, 100
```

**Current approach**: Write synonyms for all possible variations  
**Result**: Impossible. Infinite variations.

**Example**:
- `filename_priors.json` has 230 entries
- Covers ~15 doctypes
- To cover 800 doctypes: Need 12,267 entries (extrapolated)
- To cover all company variations: **Infinite entries**

---

## What Actually Breaks in Production

### Scenario 1: New Company (Same F3iche)

**Company**: ABC Garments (same industry as Green Surface)  
**Files uploaded**: `client_master.csv`, `order_sheet.xlsx`

**What happens**:
1. Filename "client_master" not in `filename_priors.json` ❌
2. Column "client_code" not in `column_priors.json` ❌
3. Classifier guesses wrong → maps to Sales Order instead of Customer ❌
4. User frustrated → churn

**Fix required**: Add entries to both JSON files + restart worker  
**Time**: 30 minutes  
**Scalable?**: No

---

### Scenario 2: New Doctype (Same ERP)

**Customer**: Wants to import "Delivery Note" (not in current 15 doctypes)

**What happens**:
1. No `mapping/Delivery Note.json` file ❌
2. Live schema fallback kicks in ✅
3. Gets field structure from Frappe ✅
4. But has zero synonyms → user columns don't map ❌

**Fix required**: Create `Delivery Note.json` with 50+ fields × 5 synonyms each  
**Time**: 3-4 hours  
**Scalable?**: No (800 doctypes = 2,400 hours)

---

### Scenario 3: New ERP Software (Odoo)

**Customer**: Wants F3Next for Odoo, not ERPNext

**What happens**:
1. Need new `odoo_doctype_graph.json` ✅ (research team work)
2. Need 148 new `mapping/*.json` files for Odoo doctypes ❌
3. Each file needs Odoo-specific synonyms ❌
4. Odoo field names different from ERPNext ❌

**Fix required**: Duplicate all 148 files, rewrite for Odoo  
**Time**: 2-3 months  
**Scalable?**: No

---

## Why This Matters for Customer Acquisition

### Green Surface Scenario

**Reality check**: Green Surface is:
- Chemical project manufacturing
- Specific file naming (they use "active_projects", "formulation")
- Specific workflows
- **We patched specifically for them**

**What happens with next customer**:
- Different file names → classifier breaks
- Different column names → mapping breaks
- Different workflows → validation breaks
- **We patch specifically for them**

**Pattern**: Every customer = new patches = technical debt explosion

---

## Root Cause Analysis

### Why Did We Create 152 Files?

**Honest timeline**:

1. **Month 1**: Built core pipeline, worked with mock data ✅
2. **Month 2**: Green Surface onboarded, files didn't match mocks ❌
3. **Fix**: Created `filename_priors.json` with "active_projects" entry
4. **Month 3**: Columns didn't map ❌
5. **Fix**: Created `column_priors.json` with manual hints
6. **Month 4**: Field mapping broke ❌
7. **Fix**: Created 148 `mapping/*.json` files with synonyms
8. **Month 5**: Merge logic broke ❌
9. **Fix**: Created `merge_policies.json`, `party_entity_rules.json`

**Pattern**: **Patch-driven development instead of architectural solution**

---

## The Fundamental Architecture Flaw

### What We Built

```
User uploads → Hardcoded rules → Manual synonyms → Guess → Patch when wrong
```

### What We Need

```
User uploads → LLM understands → Learns from data → Infers mapping → Improves over time
```

**Current**: Static, brittle, doesn't scale  
**Needed**: Dynamic, learning, scales infinitely

---

## Comparison to Working Systems

### How Stripe Handles Payment Methods

**They DON'T**:
- Have `payment_method_synonyms.json` with 10,000 variations
- Manually write "pmt_ref" → payment_reference
- Patch for each new merchant

**They DO**:
- Fine-tune model on 10M+ transactions
- Model learns patterns automatically
- New merchant = zero config

**Result**: Scales to millions of merchants

---

### How Netflix Handles User Preferences

**They DON'T**:
- Have `genre_synonyms.json` with manual mappings
- Write "action thriller" → "Action" + "Thriller"
- Patch for each user

**They DO**:
- Learn from each user's viewing history
- Build user-specific embedding space
- New user = learn from their data

**Result**: Scales to 200M+ users

---

## Summary: What Must Change

| Component | Current State | Must Become |
|-----------|--------------|-------------|
| **Doctype Classification** | Manual rules in 2 JSON files | LLM inference with embeddings |
| **Field Mapping** | 148 manual synonym files | Live schema + LLM reasoning |
| **Company Variations** | Patch per customer | Learn from customer data |
| **New Doctypes** | 3-4 hours manual work | Zero work (live schema) |
| **Research Team** | Blocked creating patches | Autonomous creating F3iches |
| **Scale Limit** | ~15 doctypes, ~5 customers | 800 doctypes, 1000+ customers |

---

## Conclusion

**Current architecture is a dead end.**

Not because code is buggy, but because **fundamental approach doesn't scale**.

No amount of patches will fix it. Needs architectural rewrite.

**Options**:
1. Ship current code to 1-2 customers, collect data, then rebuild
2. Rebuild now, ship in 2-3 months

See `06_DECISION_FRAMEWORK.md` for analysis.
