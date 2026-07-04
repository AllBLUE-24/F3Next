# KB Structure & Ownership

> **Purpose**: Define exactly what files exist, who owns them, and what they contain  
> **Audience**: Research Team + Tech Team

---

## File Organization

### Directory Structure (After Reform)

```
containers/knowledge_base/
├── common/                              # Cross-ERP knowledge
│   ├── concepts/                        # Embedding corpus (NEW)
│   │   ├── universal/                   # ~20 docs
│   │   │   ├── party_entity.md
│   │   │   ├── item_product.md
│   │   │   ├── transaction_document.md
│   │   │   ├── financial_posting.md
│   │   │   └── ...
│   │   └── f3iche_specific/             # ~50 docs
│   │       ├── garment_terminology.md
│   │       ├── chemical_terminology.md
│   │       ├── jobshop_terminology.md
│   │       └── ...
│   │
│   ├── f3iches/                         # Business model definitions
│   │   ├── garment_mto_export_b2b.json
│   │   ├── garment_wholesale_domestic.json
│   │   ├── garment_retail_chain.json
│   │   ├── chemical_batch_pharma.json
│   │   ├── chemical_continuous_process.json
│   │   ├── jobshop_machining_small.json
│   │   ├── jobshop_fabrication_large.json
│   │   └── ... (50-100 total)
│   │
│   ├── signals_registry.json            # KEEP (simplified)
│   └── mvp_bottleneck_map.json          # KEEP
│
├── erpnext/                             # ERPNext-specific
│   ├── erpnext_doctype_graph.json       # KEEP (canonical)
│   ├── erpnext_defaults_baseline.json   # KEEP
│   │
│   └── schema/                          # ❌ DELETE THIS ENTIRE FOLDER
│       ├── classification/              # ❌ DELETE (manual rules)
│       ├── corpus/                      # ❌ DELETE (business logic)
│       ├── mapping/                     # ❌ DELETE (148 files!)
│       ├── shared/                      # ❌ DELETE (move to code)
│       └── value_translation/           # ❌ DELETE (move to code)
│
└── odoo/                                # Future: Odoo support
    └── odoo_doctype_graph.json
```

---

## Ownership Matrix

| Component | Owner | Changes When | Approval Needed |
|-----------|-------|--------------|-----------------|
| **F3iche JSONs** | Research Team | New business model onboarded | Product review |
| **Concept docs** | Research Team | Quarterly enrichment | Tech review (embeddings) |
| **Doctype graph** | Research Team | New ERP doctype discovered | ERP specialist |
| **signals_registry** | Research Team | New F3iche niche added | None |
| **Company learning** | Code (automatic) | Each file upload | None |
| **Live schema** | Customer's ERP | Customer changes ERP | None |
| **LLM inference** | Code | Model improvement | Tech lead |

---

## File Specifications

### 1. F3iche Definition (Research Team)

**Location**: `common/f3iches/{f3iche_id}.json`

**Template**:
```json
{
  "f3iche_id": "garment_mto_export_b2b",
  "version": "1.0",
  "created_date": "2026-07-01",
  "owner": "Research Team",
  
  "classification": {
    "industry": "garment",
    "sub_industry": "apparel_manufacturing",
    "business_model": "made-to-order",
    "customer_segment": "B2B_export"
  },
  
  "description": {
    "short": "Garment manufacturers doing made-to-order for international brands",
    "long": "Companies that receive POs from international buyers (H&M, Zara, etc.), create style-wise production plans, manage size/color variants, and export finished garments.",
    "typical_companies": ["Export garment units", "Buying house manufacturers", "OEM apparel factories"]
  },
  
  "terminology_patterns": {
    "items": {
      "primary_terms": ["style_code", "design_no", "article"],
      "secondary_terms": ["po_style", "style_number", "garment_code"],
      "avoid_confusion": "In garment context, 'style' = 'item', not 'item_group'"
    },
    "customers": {
      "primary_terms": ["buyer", "brand", "importer"],
      "secondary_terms": ["client", "customer", "buyer_name"],
      "avoid_confusion": "Buyers are the brands, not retailers"
    },
    "orders": {
      "primary_terms": ["po_number", "style_po", "order_ref"],
      "secondary_terms": ["buyer_po", "purchase_order", "order_no"],
      "avoid_confusion": "PO = buyer's purchase order, not our purchase"
    },
    "manufacturing": {
      "primary_terms": ["cut_plan", "marker", "sew_plan"],
      "secondary_terms": ["cutting_order", "lay_plan", "production_plan"],
      "avoid_confusion": "Cut plan = internal production schedule"
    }
  },
  
  "file_naming_patterns": {
    "high_confidence": [
      "buyer_po", "style_master", "cut_plan", "order_breakdown",
      "size_breakdown", "color_breakdown", "pack_ratio"
    ],
    "medium_confidence": [
      "orders", "styles", "production", "buyers", "clients"
    ]
  },
  
  "workflow_characteristics": {
    "order_structure": "Orders broken down by: style × color × size",
    "bom_pattern": "BOM per style-color-size combination (high variant count)",
    "manufacturing": "Cut → sew → finish → pack → ship",
    "quality": "Inline QC during sewing, final AQL inspection before ship"
  },
  
  "key_doctypes": {
    "must_have": ["Item", "Customer", "BOM", "Work Order", "Sales Order"],
    "commonly_used": ["Purchase Order", "Stock Entry", "Delivery Note"],
    "rarely_used": ["Purchase Receipt", "Sales Invoice"]
  },
  
  "bottlenecks": [
    {
      "issue": "Size/color variant explosion",
      "impact": "Hundreds of BOMs per style",
      "solution": "Variant item management, BOM templates"
    },
    {
      "issue": "Fabric wastage tracking",
      "impact": "Margins depend on cutting efficiency",
      "solution": "Marker efficiency reporting, wastage tracking"
    }
  ],
  
  "validation_rules": {
    "sales_order": [
      "Must have size breakdown (S/M/L/XL)",
      "Must have color breakdown",
      "Delivery date typically 60-90 days from order"
    ],
    "bom": [
      "Must specify fabric per garment",
      "Must include trims (buttons, zippers, labels)",
      "Wastage % must be realistic (15-25%)"
    ]
  }
}
```

**When to create**: New business model (1-2 per month)  
**Who reviews**: Product team + ERP specialist  
**Embedding**: Yes - entire JSON embedded for semantic search

---

### 2. Concept Document (Research Team)

**Location**: `common/concepts/universal/party_entity.md`

**Template**:
```markdown
# Party Entity (Universal ERP Concept)

## Definition
A business entity you trade with - someone you sell to or buy from.

## ERP System Variations

### ERPNext
- **Customer**: Party who buys from you
- **Supplier**: Party who sells to you
- Separate doctypes, each with own master

### SAP
- **Business Partner (BP)**: Single entity
- Role flag determines if customer/supplier/both
- Unified address book

### Odoo
- **res.partner**: Single model
- customer/supplier boolean flags
- Can be both simultaneously

## Common User Terminology

### Customer Side
- **Primary**: client, buyer, customer, account, party
- **Regional**: retailer (retail), brand (manufacturing), distributor (wholesale)
- **Industry-specific**: 
  - Garment: buyer, importer, brand
  - Chemical: distributor, end_user
  - Job shop: client, project_owner

### Supplier Side
- **Primary**: vendor, supplier, seller, wholesaler
- **Regional**: dealer, trader, merchant
- **Industry-specific**:
  - Garment: fabric_supplier, trim_vendor
  - Chemical: raw_material_supplier, ingredient_vendor
  - Job shop: material_supplier, subcontractor

## Column Name Patterns

### Identity Fields
- party_name, customer_name, client_name, ledger_name, account_name
- vendor_name, supplier_name, seller_name
- buyer_code, party_code, account_no, customer_id

### Grouping/Category
- customer_group, party_type, customer_category, segment
- supplier_group, vendor_type

### Contact
- contact_person, primary_contact, account_manager
- phone, mobile, email, address

### Financial
- credit_limit, payment_terms, credit_days
- outstanding_balance, ledger_balance

## File Naming Patterns
- **Customer**: clients.csv, customers.xlsx, parties.csv, accounts.csv, buyers.xlsx, ledger.csv
- **Supplier**: vendors.csv, suppliers.xlsx, sellers.csv

## Data Validation Clues

### This is likely a Party file if:
- Has "name" + "contact" + "address" columns
- Has financial terms (credit_limit, payment_terms)
- Small number of rows (10-1000, not 10,000+)
- Text-heavy (names, addresses), not numeric-heavy

### Customer vs Supplier hints:
- Customer: "buyer", "client", "sales", "invoice_to"
- Supplier: "vendor", "purchase", "bill_from"

## Mapping Tips

### When column is ambiguous:
- "party_name" → Check F3iche context
  - B2B manufacturing → likely "customer" (their buyers)
  - Retail → could be either
- "code" → Check for prefixes
  - "CUST-" → customer
  - "SUPP-" → supplier

### When file contains both:
- Look for "type" or "category" column
- Split into separate doctypes (Customer + Supplier)
- Use party_entity_rules for resolution

## Industry-Specific Notes

### Garment Manufacturing (MTO Export)
- Customers = International buyers (H&M, Zara, Uniqlo)
- Usually called "buyer" or "brand" (NOT "customer")
- Suppliers = Fabric mills, trim vendors, subcontractors

### Chemical Batch Manufacturing
- Customers = Distributors, wholesalers, pharma companies
- Often called "distributor" or "end_user"
- Suppliers = Raw material suppliers, ingredient vendors

### Job Shop Manufacturing
- Customers = Project-based clients
- Usually called "client" or "account"
- Suppliers = Material suppliers, subcontractors
```

**When to create**: Initial corpus creation (1-2 weeks) + quarterly enrichment  
**Who reviews**: Tech team (for embedding quality)  
**Embedding**: Yes - chunks embedded with metadata

---

### 3. Doctype Graph (Research Team)

**Location**: `erpnext/erpnext_doctype_graph.json`

**What to keep**: Everything! This file is excellent.

**When to update**:
- New doctype discovered in ERPNext
- New dependency relationship found
- New validation rule (compliance-driven)

**Format** (already correct):
```json
{
  "Customer": {
    "module": "Selling",
    "layer": 3,
    "depends_on": ["Customer Group", "Territory"],
    "required_fields": ["customer_name", "customer_group", "territory"],
    "link_fields": {
      "customer_group": "Customer Group",
      "territory": "Territory"
    }
  }
}
```

**Maintenance**: Add 1-2 entries per month as scope expands

---

### 4. Company Knowledge Space (Code - Automatic)

**Location**: Database per project + Embedding namespace

**Schema**:
```python
# Database: is_company_knowledge table
{
  "project_id": "uuid",
  "f3iche": "garment_mto_export_b2b",
  "learned_terms": {
    "Customer::buyer_name": "customer_name",
    "Customer::client_code": "customer",
    "Item::style_code": "item_code",
    "Sales Order::po_ref": "po_no"
  },
  "observed_columns": [
    "buyer_name", "style_code", "po_ref", "color", "size", ...
  ],
  "observed_filenames": [
    "buyer_po.xlsx", "style_master.csv", "order_breakdown.xlsx"
  ],
  "embedding_namespace": "company_abc123",
  "created_at": "2026-07-01T10:00:00Z",
  "updated_at": "2026-07-05T14:30:00Z"
}

# Vector DB: company_abc123 namespace
[
  {
    "text": "Company uses 'buyer_name' for customer identity",
    "metadata": {"field": "customer_name", "doctype": "Customer"}
  },
  {
    "text": "Company uses 'style_code' for item/product identity",
    "metadata": {"field": "item_code", "doctype": "Item"}
  }
]
```

**Maintenance**: Automatic (code learns from uploads)

---

## What Gets Deleted

### Delete Immediately (152 files)

```bash
# Run these commands to delete patch files:

# Delete all manual mapping files (148 files)
rm -rf containers/knowledge_base/erpnext/schema/mapping/

# Delete manual classification rules
rm containers/knowledge_base/erpnext/schema/classification/filename_priors.json
rm containers/knowledge_base/erpnext/schema/classification/column_priors.json
rm containers/knowledge_base/erpnext/schema/classification/global_hints.json

# Delete business logic JSON files (move to code first)
rm containers/knowledge_base/erpnext/schema/corpus/merge_policies.json
rm containers/knowledge_base/erpnext/schema/corpus/party_entity_rules.json

# Delete entire schema folder (after code migration)
rm -rf containers/knowledge_base/erpnext/schema/
```

**Before deleting**: Migrate business logic to Python (see `04_IMPLEMENTATION_PLAN.md`)

---

## What Gets Created

### Create: Concept Docs (~70 files)

**Universal concepts** (`common/concepts/universal/`, ~20 files):
1. party_entity.md
2. item_product.md
3. transaction_document.md
4. financial_posting.md
5. inventory_movement.md
6. manufacturing_order.md
7. quality_control.md
8. batch_lot.md
9. serial_number.md
10. price_list.md
11. payment_entry.md
12. journal_entry.md
13. tax_template.md
14. warehouse_location.md
15. uom_unit.md
16. currency_exchange.md
17. territory_geography.md
18. department_cost_center.md
19. project_job.md
20. timesheet_attendance.md

**F3iche-specific terminology** (`common/concepts/f3iche_specific/`, ~50 files):
- garment_terminology.md
- chemical_terminology.md
- jobshop_terminology.md
- retail_terminology.md
- trading_terminology.md
- services_terminology.md
- ... (one per F3iche, grows over time)

**Maintenance**: Research team writes initial corpus (1-2 weeks), enriches quarterly

---

### Create: Narrow F3iches (50-100 files)

**Current F3iches** (5 broad ones):
- manufacturing_garment_variants.json
- manufacturing_project_chemical.json
- manufacturing_fabrication_jobshop.json
- manufacturing_food_batch.json
- (1 more?)

**New F3iches** (50-100 narrow ones):

**Garment Industry** (10-15 F3iches):
- garment_mto_export_b2b.json
- garment_mto_export_b2c.json
- garment_wholesale_domestic.json
- garment_retail_chain.json
- garment_fabric_manufacturing.json
- garment_accessories.json
- garment_home_textiles.json
- garment_technical_textiles.json
- ...

**Chemical Industry** (10-15 F3iches):
- chemical_batch_pharma.json
- chemical_batch_specialty.json
- chemical_continuous_process.json
- chemical_mixing_blending.json
- chemical_formulation_lab.json
- chemical_distribution_only.json
- ...

**Job Shop** (10-15 F3iches):
- jobshop_machining_small.json
- jobshop_machining_large.json
- jobshop_fabrication_sheet_metal.json
- jobshop_fabrication_structural.json
- jobshop_assembly.json
- jobshop_tooling_dies.json
- ...

**Maintenance**: Research team creates 2-3 per month as new verticals onboard

---

## Embedding Strategy

### What to Embed

1. **F3iche JSONs**: Entire content (for semantic F3iche discovery)
2. **Concept docs**: Chunked by section (for terminology lookup)
3. **Company context**: Per-project namespace (for company-specific learning)

### Embedding Namespaces

```python
# Global namespaces (shared across all projects)
"f3iche_registry"           # All F3iche definitions
"universal_concepts"        # Universal ~20 concept docs
"f3iche_garment"            # Garment-specific concepts
"f3iche_chemical"           # Chemical-specific concepts
# ... one namespace per F3iche

# Per-project namespaces (company-specific learning)
"company_abc123"            # Company ABC's learned terms
"company_xyz789"            # Company XYZ's learned terms
# ... one namespace per project
```

### Embedding Update Schedule

| Namespace | Update When | Who Triggers |
|-----------|-------------|--------------|
| f3iche_registry | New F3iche added | Research team |
| universal_concepts | Quarterly enrichment | Research team |
| f3iche_* | Quarterly enrichment | Research team |
| company_* | Each file upload | Code (automatic) |

---

## Migration Checklist

### Phase 1: Create New Structure (Week 1)

- [ ] Create `common/concepts/` directory
- [ ] Write 20 universal concept docs
- [ ] Split 5 broad F3iches into 15-30 narrow ones
- [ ] Set up embedding pipeline
- [ ] Embed all new docs

### Phase 2: Migrate Business Logic (Week 2)

- [ ] Move `merge_policies.json` logic → `corpus_merge.py` (Python)
- [ ] Move `party_entity_rules.json` → `entity_resolver.py` (Python)
- [ ] Move validation rules → `validation_engine.py` (Python)
- [ ] Add unit tests for migrated logic

### Phase 3: Delete Old Files (Week 2, after migration)

- [ ] Delete `mapping/*.json` (148 files)
- [ ] Delete `classification/*.json` (3 files)
- [ ] Delete `corpus/*.json` (2 files)
- [ ] Delete entire `schema/` folder
- [ ] Update `.gitignore` if needed

### Phase 4: Update Code (Week 3)

- [ ] Rewrite classifier to use LLM + embeddings
- [ ] Rewrite mapper to use live schema + company learning
- [ ] Add company knowledge space DB table
- [ ] Add company embedding namespaces
- [ ] Update tests

---

## Success Metrics

**After migration, should achieve**:

1. ✅ New customer upload → **0 KB file changes**
2. ✅ New F3iche → **1 JSON + 2-3 concept docs**
3. ✅ New doctype → **0 changes** (live schema handles it)
4. ✅ Mapping accuracy → **90%+ on first upload**
5. ✅ Mapping accuracy → **95%+ after 3 uploads** (company learning kicks in)

**KB file count**:
- Before: 155+ files (growing constantly)
- After: ~125 files (F3iches + concepts, grows slowly)

**Maintenance burden**:
- Before: Every customer needs patches
- After: Every 10 customers might need 1 new F3iche
