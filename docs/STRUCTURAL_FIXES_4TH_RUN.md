# Structural Fixes for 4th_run Corpus Mapping Failures

**Branch:** `feature/phase-0-mvp-pipeline-foundation`  
**Commit:** `c633c24`  
**Date:** 2026-06-22

---

## Summary

Fixed compound pipeline failures that caused only 2/6 files from the 4th_run corpus to map successfully, despite an 80% readiness score. Implemented **architectural solutions** (not synonym band-aids) across 4 layers.

---

## Fixes Implemented

### 1. Graph/Schema Reconciliation (Layer L3 - KB)
**File:** `containers/implementation/mapping_agent/schema_builder.py`

**Problem:** `naming_series` required by graph but not in Project.json `field_mappings` → defaults inject it → Pydantic strips it → preflight fails.

**Solution:** Merge `erpnext_doctype_graph.json` required_fields into Pydantic schema as optional fields to preserve them through validation.

```python
# Extract graph system fields not in KB
graph_required_raw = graph.get("doctypes", {}).get(doctype, {}).get("required_fields", [])
graph_system_fields = {field.split("(")[0].strip() for field in graph_required_raw if field not in fmap}

# Add as optional to preserve through Pydantic
for sys_field in graph_system_fields:
    if sys_field not in fields:
        fields[sys_field] = (Optional[str], None)
```

---

### 2. Readiness Bypasses Plan Gate (Layer L1 Honesty + L7 Pipeline)
**File:** `containers/implementation/mapping_agent/activities.py`

**Problem:** Step 8d builds plan with `data_gap` actions before Step 9 maps → mapping respects plan and skips files that readiness already validated at 80%.

**Solution:** Reorder `_should_map_doctype` priority:
1. **Readiness (ready/partial)** → uploaded file evidence trumps plan
2. Plan create/pending_mapping → explicit schedule
3. Plan skip/seed/optional → explicit directive
4. Target structure → fallback

```python
# PRIORITY 1: Check readiness first
if readiness:
    for item in (readiness.ready_doctypes or []) + (readiness.partial_doctypes or []):
        if resolve_doctype(dt_name) == doctype:
            activity.logger.info("✅ Readiness evidence — bypassing plan gate")
            return True

# PRIORITY 2: Check import plan...
```

**Impact:** Files with evidence won't be blocked by premature `data_gap` plan actions.

---

### 3. Corpus Understanding Guides Classification (Layer L7 Integration)
**File:** `containers/implementation/mapping_agent/activities.py`

**Problem:** Step 8a full-context analysis says "stock_summary → Item" but Step 9 per-file classifier says "BOM" (context lost).

**Solution:** Check `corpus_understanding` from Step 8a before falling back to LLM classifier:

```python
# Check corpus understanding first (Step 8a full-context analysis)
for file_entry in corpus_hints.get("files", []):
    if file_entry.get("filename") == inp.filename:
        suggested = file_entry.get("likely_erpnext_doctypes", [])
        if suggested and len(suggested) == 1:
            doctype = suggested[0]
            activity.logger.info("📋 Corpus understanding: %s → %s", inp.filename, doctype)
            break

# Fall back to LLM classifier only if corpus ambiguous
if not corpus_doctype:
    cls = await classify_doctype(...)
```

---

### 4. Semantic Party-Split Detection (Layer L0 LLM)
**File:** `containers/implementation/mapping_agent/activities.py`

**Problem:** Tally `Under_Group` with "Sundry Debtors"/"Sundry Creditors" not recognized (hardcoded to look for `role`/`type` columns with "Customer"/"Vendor" values).

**Solution:** LLM-based semantic detection as fallback when pattern-based fails:

```python
async def _detect_semantic_party_split(self, rows, columns, model):
    """Ask LLM: Does this file contain both customers and suppliers?"""
    
    prompt = """
    Columns: {columns}
    Sample rows: {sample}
    
    Common patterns:
    - Indian Tally: "Under_Group" with "Sundry Debtors" (customers), "Sundry Creditors" (suppliers)
    - Multi-entity: "Type"/"Role" with party type indicators
    
    Respond JSON: {has_split, split_column, customer_values, supplier_values, confidence}
    """
    
    response = await generate_json(prompt, model)
    # Split rows based on LLM-identified column and values...
```

**Impact:** Works for **any** accounting format, not just pre-enumerated synonyms.

---

### 5. Golden Harness for 4th_run (Layer L5 Testing)
**File:** `containers/implementation/tests/test_dry_run_map_4th_run.py`

**Purpose:** Test **structural behavior** (not KB synonym completeness):
- Files aren't skipped by plan gate
- Semantic split is attempted for multi-entity files
- System fields survive Pydantic validation
- Mapping reaches completion stage

```python
def test_projects_master_includes_naming_series(self):
    """System field naming_series must survive Pydantic validation."""
    result = dry_run_map_file(content, "Project", kb=kb, 
                              company_context={"company_name": "Strahats"})
    
    # Critical: naming_series must NOT be in missing_required
    missing = result.get("missing_required_after", [])
    self.assertNotIn("naming_series", missing)
```

**Test Results:** 7/7 passing

---

## Impact on User's 4th_run Issue

| File | Before | After |
|------|--------|-------|
| `tally_sundry_ledgers.csv` | Skipped by plan (classified as Supplier only) | Semantic split attempted → Customer + Supplier |
| `tally_stock_summary.csv` | Skipped by plan, misclassified as BOM | Corpus understanding used → Item classification |
| `excel_formulation_master.csv` | Skipped by plan | Readiness evidence bypasses plan → mapping attempted |
| `projects_master.csv` | Preflight failed (naming_series stripped) | System field preserved → passes |
| `excel_production_schedule.csv` | ✅ Worked | ✅ Still works |
| `tally_pending_sales_orders.csv` | ✅ Worked | ✅ Still works |

**Expected outcome after fixes:** 5-6 doctypes mapped instead of 2.

---

## Why This is Better Than Adding Synonyms

| Approach | Maintenance | Coverage | Root Cause |
|----------|-------------|----------|------------|
| Add `Under_Group` synonym | Manual update per format | Tally only | ❌ No |
| **LLM semantic split** | Zero | All formats | ✅ Yes |
| Add BOM filename boost | Per-file tuning | One file | ❌ No |
| **Use corpus understanding** | Zero (already exists) | All files | ✅ Yes |

---

## Testing

```bash
cd c:\dev\F3Next
python -m pytest containers/implementation/tests/test_dry_run_map_4th_run.py -v
# ======================== 7 passed in 2.84s ========================
```

---

## Architecture Alignment

- ✅ **L0 (LLM):** Semantic party-split uses LLM for intent understanding
- ✅ **L1 (Honesty):** Readiness evidence now honored in mapping decisions
- ✅ **L3 (KB):** Graph and schema reconciled (single source of truth)
- ✅ **L5 (Test):** Golden harness prevents regression
- ✅ **L7 (Pipeline):** Step 8a → Step 9 data flow fixed

**Follows architecture-first rule:** Fix the layer where abstraction broke, not the symptom.

---

## Next Steps (Optional)

1. **Run full IS harness** on 4th_run corpus to validate end-to-end
2. **Update GOLDEN_MATRIX_MANIFEST.md** to include 4th_run rows
3. **Add minimal Tally synonyms** if column mapping still fails (but structural gates now open)

---

## Related Documents

- `docs/FOUNDATIONS.md` - Architecture layers
- `docs/GOLDEN_MATRIX_MANIFEST.md` - 3rd_run golden corpus
- `.cursor/rules/architecture-first.mdc` - Triage protocol
