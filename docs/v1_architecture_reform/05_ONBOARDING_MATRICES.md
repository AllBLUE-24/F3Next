# Onboarding Matrices - What Changes When

> **Purpose**: Define exactly what files/code need updating for each onboarding scenario  
> **Goal**: New customer = ZERO changes

---

## Onboarding Scenarios

| Scenario | Frequency | Target: Changes Required |
|----------|-----------|-------------------------|
| New customer (same F3iche) | Every week | 0 files, 0 code |
| New customer (new F3iche) | Every 2-4 weeks | 1-3 KB files only |
| New doctype (known ERP) | Every 2-3 months | 1 line in graph |
| New ERP software | Every 1-2 years | 1 graph + 1 adapter |

---

## Matrix 1: New Customer (Same F3iche)

**Scenario**: ABC Garments signs up. Same industry as Green Surface (chemical project manufacturing).

### Current Architecture (BROKEN)

| Step | What Breaks | Fix Required | Time |
|------|-------------|--------------|------|
| Upload files | Filenames don't match `filename_priors.json` | Add entries, restart worker | 30 min |
| Classify | Columns don't match `column_priors.json` | Add entries, restart worker | 30 min |
| Map fields | Synonyms not in `mapping/*.json` files | Edit 5-10 JSON files | 2-3 hours |
| Validation | New validation rules | Edit `validation_rules.json` | 1 hour |
| Import | Merge logic edge case | Patch `merge_policies.json` | 1 hour |

**Total**: 5-6 hours of patching + worker restart + testing

**Result**: Customer waits 1-2 days for "fixes"

---

### Proposed Architecture (SCALABLE)

| Step | What Happens | Changes Required | Time |
|------|--------------|------------------|------|
| Upload files | Company learning extracts terminology | 0 files, 0 code | Automatic |
| Classify | LLM infers doctype using F3iche context | 0 files, 0 code | Automatic |
| Map fields | LLM maps columns using live schema + company learning | 0 files, 0 code | Automatic |
| Validation | Uses doctype graph + live schema | 0 files, 0 code | Automatic |
| Import | Python logic handles merge | 0 files, 0 code | Automatic |

**Total**: 0 changes

**Result**: Customer goes live same day

---

### Example: Files from Different Company

**Company A** (Green Surface):
```csv
# formulation_master.csv
formulation_id, batch_code, composition, target_qty
FORM-001, BATCH-A, NaCl-95%, 500kg
```

**Company B** (ABC Chemicals):
```csv
# product_list.xlsx  ← Different filename
product_code, recipe_no, ingredients, lot_size  ← Different columns
PROD-A01, REC-001, Sodium-90%, 1000kg
```

**Current system**: Breaks. Needs patches.

**Proposed system**:
1. Company B uploads → Company learning extracts: `product_code`, `recipe_no`, etc.
2. LLM sees F3iche = `chemical_batch_pharma`
3. LLM infers: `product_list.xlsx` → Item doctype (chemical context)
4. LLM maps: `product_code` → `item_code`, `recipe_no` → `bom_no`
5. Works automatically

---

## Matrix 2: New Customer (New F3iche)

**Scenario**: XYZ Retail Chain signs up. Different F3iche (retail, not manufacturing).

### Current Architecture (BROKEN)

| Step | What Breaks | Fix Required | Time |
|------|-------------|--------------|------|
| Discovery | No F3iche for retail chain | Research team writes new F3iche | 2-3 days |
| Signals registry | No scoring rules for retail | Add to `signals_registry.json` | 1 day |
| Classification | No filename/column priors for retail terms | Add 50+ entries to JSONs | 1 day |
| Mapping | No KB modules for retail doctypes | Create 10+ `mapping/*.json` files | 3-4 days |

**Total**: 1-2 weeks of KB + code work

---

### Proposed Architecture (SCALABLE)

| Step | What Changes | Owner | Time |
|------|--------------|-------|------|
| F3iche creation | Create `retail_chain_grocery.json` | Research | 2-4 hours |
| Concept docs | Write `retail_terminology.md` (maybe 2-3 docs) | Research | 2-4 hours |
| Embedding | Embed new F3iche + concepts | Code (automatic) | 5 min |
| Everything else | Works automatically via LLM | None | 0 |

**Total**: 4-8 hours (research only, zero code)

**Files changed**: 1 F3iche JSON + 2-3 concept docs

---

### Example: Retail Chain F3iche

**Create**: `common/f3iches/retail_chain_grocery.json`
```json
{
  "f3iche_id": "retail_chain_grocery",
  "industry": "retail",
  "business_model": "multi-store grocery chain",
  "customer_segment": "B2C consumers",
  
  "terminology_patterns": {
    "items": ["sku", "product_code", "upc", "barcode"],
    "locations": ["store", "outlet", "branch", "location"],
    "transactions": ["pos_sale", "receipt", "transaction"],
    "inventory": ["stock_on_hand", "shelf_qty", "backroom_qty"]
  },
  
  "file_naming_patterns": [
    "products", "sku_master", "inventory", "store_list", "pos_sales"
  ],
  
  "workflow_characteristics": {
    "order_structure": "Daily POs to distribution center",
    "inventory": "Store-wise stock tracking",
    "pricing": "Promotional pricing per store"
  },
  
  "key_doctypes": ["Item", "Warehouse", "Stock Entry", "Sales Invoice", "Delivery Note"]
}
```

**Create**: `common/concepts/f3iche_specific/retail_terminology.md`
```markdown
# Retail Industry Terminology

## Items
- **SKU**: Stock Keeping Unit - unique product identifier
- Common columns: sku, product_code, upc, barcode, ean
- NOT called "item_code" or "part_number" (that's manufacturing)

## Locations
- **Store**: Physical retail location
- Maps to: Warehouse in ERPNext
- Common columns: store_id, outlet_code, branch_code

## Transactions
- **POS Sale**: Point of sale transaction
- Maps to: Sales Invoice in ERPNext
- Common columns: receipt_no, transaction_id, pos_id
```

**Embed**: `python scripts/embed_kb.py` (automatic)

**Done**: Retail customers now work automatically

---

## Matrix 3: New Doctype (Same ERP)

**Scenario**: Customer wants to import "Delivery Note" (not in current 15 doctypes).

### Current Architecture (BROKEN)

| Step | What's Needed | Time |
|------|---------------|------|
| Create mapping KB | Write `mapping/Delivery Note.json` with 50+ fields × 5 synonyms | 3-4 hours |
| Add to classifier | Update `filename_priors.json`, `column_priors.json` | 30 min |
| Add merge rules | Update `merge_policies.json` with dedupe key | 15 min |
| Add to graph | Update `erpnext_doctype_graph.json` | 15 min |

**Total**: 4-5 hours manual work

**Scalable?**: No. 800 doctypes × 4 hours = 3,200 hours (1.6 years!)

---

### Proposed Architecture (SCALABLE)

| Step | What Happens | Changes Required | Time |
|------|--------------|------------------|------|
| Add to graph | Add doctype entry to `erpnext_doctype_graph.json` | 1 entry (5-10 lines) | 10 min |
| Live schema | Fetch from customer's ERPNext automatically | 0 (automatic) | 0 |
| Classification | LLM infers from filename + columns | 0 (automatic) | 0 |
| Mapping | LLM maps using live schema | 0 (automatic) | 0 |

**Total**: 10 minutes (research adds 1 graph entry)

**Scalable?**: Yes. 800 doctypes × 10 min = 133 hours (3 weeks, done!)

---

### Example: Add Delivery Note

**Update**: `erpnext/erpnext_doctype_graph.json`
```json
{
  "Delivery Note": {
    "module": "Stock",
    "layer": 6,
    "depends_on": ["Customer", "Item", "Warehouse", "Sales Order"],
    "required_fields": ["customer", "posting_date", "items"],
    "link_fields": {
      "customer": "Customer",
      "items[].item_code": "Item",
      "items[].warehouse": "Warehouse"
    }
  }
}
```

**That's it!**

Everything else (field schema, synonyms, mapping) handled by:
- Live Frappe API (gets actual fields from customer's ERPNext)
- LLM (infers column→field mapping)
- Company learning (remembers customer's terminology)

---

## Matrix 4: New ERP Software (e.g., Odoo)

**Scenario**: Customer using Odoo (not ERPNext).

### Current Architecture (IMPOSSIBLE)

Would need:
- New graph: `odoo_doctype_graph.json`
- 148 new files: `mapping_odoo/*.json`
- New priors: `odoo_filename_priors.json`, `odoo_column_priors.json`
- Code changes: Odoo-specific validation logic

**Time**: 2-3 months minimum

**Scalable?**: No.

---

### Proposed Architecture (SCALABLE)

| Step | What's Needed | Owner | Time |
|------|---------------|-------|------|
| Create graph | Write `odoo/odoo_doctype_graph.json` | Research | 1-2 weeks |
| Create adapter | Write `shared/erp_adapters/odoo.py` | Tech | 2-3 weeks |
| Concept docs | Write Odoo-specific terminology (if different) | Research | 1 week |
| Everything else | Works automatically via LLM + live Odoo API | None | 0 |

**Total**: 4-6 weeks (one-time, then infinite Odoo customers)

**Files created**: 1 graph + 1 adapter + 5-10 concept docs

**NOT created**: 148 mapping files, priors, etc.

---

### Example: Odoo Doctype Graph

**Create**: `odoo/odoo_doctype_graph.json`
```json
{
  "_meta": {
    "erp_system": "Odoo",
    "version": "17.0",
    "description": "Odoo doctype dependency graph"
  },
  
  "res.partner": {
    "module": "base",
    "layer": 3,
    "depends_on": ["res.country", "res.country.state"],
    "required_fields": ["name"],
    "notes": "Single model for Customer/Supplier (use is_customer/is_supplier flags)"
  },
  
  "product.product": {
    "module": "product",
    "layer": 3,
    "depends_on": ["product.category", "uom.uom"],
    "required_fields": ["name", "uom_id"],
    "notes": "Product variant (with template product.template)"
  }
}
```

**Create**: `shared/erp_adapters/odoo.py`
```python
class OdooAdapter(ERPAdapter):
    """Odoo XML-RPC adapter"""
    
    async def get_doctype_schema(self, model: str) -> List[Dict]:
        """Fetch fields from Odoo model"""
        # Use Odoo XML-RPC: models.execute_kw('fields_get')
        ...
    
    async def create_record(self, model: str, values: Dict) -> str:
        """Create record in Odoo"""
        # Use Odoo XML-RPC: models.execute_kw('create')
        ...
```

**Done**: All Odoo customers work automatically

---

## Summary Matrix

| Scenario | Current System | Proposed System |
|----------|---------------|-----------------|
| **New customer (same F3iche)** | 5-6 hours patching | 0 changes (automatic) |
| **New customer (new F3iche)** | 1-2 weeks | 4-8 hours (research only) |
| **New doctype (same ERP)** | 4-5 hours | 10 min (1 graph entry) |
| **New ERP software** | 2-3 months | 4-6 weeks (one-time setup) |

---

## Onboarding Cost Comparison

### Current (At Scale)

Assuming 100 customers, 50 doctypes, 2 ERPs:

| Activity | Volume | Time per | Total Time |
|----------|--------|----------|------------|
| Customer patches | 100 | 5 hours | 500 hours |
| Doctype KB files | 50 | 4 hours | 200 hours |
| ERP setup | 2 | 2 months | 4 months |

**Total**: 700 hours + 4 months = **~1.5 years of work**

**Team needed**: 3-4 people full-time just for KB maintenance

---

### Proposed (At Scale)

Same 100 customers, 50 doctypes, 2 ERPs:

| Activity | Volume | Time per | Total Time |
|----------|--------|----------|------------|
| Customer onboarding | 100 | 0 hours | 0 hours |
| New F3iches | 20 | 6 hours | 120 hours |
| Doctype graph entries | 50 | 10 min | 8 hours |
| ERP setup | 2 | 5 weeks | 10 weeks |

**Total**: 128 hours + 10 weeks = **~4 months of work**

**Team needed**: 1 research person part-time

---

## Scaling Economics

### Break-Even Analysis

**Rebuild cost**: 8-10 weeks engineering = ~$50K

**Savings per customer** (after rebuild):
- Current: 5 hours × $100/hr = $500
- Proposed: 0 hours = $0
- **Savings**: $500 per customer

**Break-even**: $50K / $500 = **100 customers**

After 100 customers, rebuild has paid for itself.

---

### At 1000 Customers

**Current system** (if it could scale):
- 1000 × 5 hours = 5,000 hours
- 5,000 hours / 2000 hours/year = 2.5 FTE
- 2.5 FTE × $100K salary = **$250K/year in KB maintenance**

**Proposed system**:
- 1000 customers × 0 hours = 0 hours
- New F3iches: ~50 total × 6 hours = 300 hours
- 300 hours / 2000 hours/year = 0.15 FTE
- 0.15 FTE × $100K = **$15K/year**

**Annual savings at 1000 customers**: $235K

---

## Conclusion

**Current architecture**: Doesn't scale beyond 10-20 customers

**Proposed architecture**: Scales to 1000+ customers with minimal maintenance

**ROI**: Positive after 100 customers, massive after 1000

**Decision**: See `06_DECISION_FRAMEWORK.md`
