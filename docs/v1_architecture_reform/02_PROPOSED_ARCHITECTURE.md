# Proposed Architecture - How to Fix It

> **Goal**: Support infinite companies, any terminology, zero per-customer config  
> **Approach**: Multi-layer knowledge system with learning

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│ LAYER 0: Narrow F3iche Registry (Research Team)            │
│ ├─ 50-100 specific F3iches (not 5 broad ones)              │
│ ├─ Each has: industry + business model + typical terms     │
│ └─ Example: "garment_mto_export_b2b" (not "manufacturing") │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ LAYER 1: Company Knowledge Space (Code - Per Project)      │
│ ├─ Learn from company's first 3-5 file uploads             │
│ ├─ Extract: columns, filenames, terminology patterns       │
│ ├─ Build: company-specific embedding space                 │
│ └─ Remember: "style_code" → item_code (for THIS company)   │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ LAYER 2: Live ERP Schema (Frappe API - Already Built)      │
│ ├─ Fetch actual field structure from customer's ERPNext    │
│ ├─ Works for ANY doctype (even custom ones)                │
│ ├─ Auto-generates basic synonyms (fieldname + label)       │
│ └─ PRIMARY source (not fallback anymore)                   │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ LAYER 3: LLM Inference Engine (Last Resort)                │
│ ├─ Uses context from Layers 0-2                            │
│ ├─ Infers doctype from filename + columns + F3iche         │
│ ├─ Maps columns to fields with reasoning                   │
│ └─ Only called when Layers 0-2 don't have high confidence  │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ LAYER 4: Feedback Loop (Future - After 100 Customers)      │
│ ├─ Collect successful mappings across all customers        │
│ ├─ Fine-tune model on F3Next-specific patterns             │
│ ├─ Accuracy improves from 90% → 95%+                       │
│ └─ Optional - can ship without this                        │
└─────────────────────────────────────────────────────────────┘
```

---

## Layer 0: Narrow F3iche Registry

### Current Problem

**Today**: 5 broad F3iches
```json
{
  "f3iche_id": "manufacturing_garment_variants",
  "description": "All garment manufacturing businesses"
}
```

**Problem**: Too vague. Garment includes:
- Made-to-order export (uses "buyer", "style_code", "cut_plan")
- Wholesale domestic (uses "retailer", "design_no", "stock")
- Retail chain (uses "store", "sku", "inventory")

Can't write generic synonyms that cover all.

---

### Proposed: 50-100 Narrow F3iches

**Example 1**: Garment Export B2B
```json
{
  "f3iche_id": "garment_mto_export_b2b",
  "industry": "garment",
  "business_model": "made-to-order for international brands",
  "customer_segment": "B2B export (H&M, Zara, etc.)",
  
  "terminology_patterns": {
    "items": ["style_code", "design_no", "po_style", "article"],
    "customers": ["buyer", "brand", "importer", "client"],
    "orders": ["po_number", "style_po", "order_ref"],
    "manufacturing": ["cut_plan", "marker", "sew_plan"]
  },
  
  "file_naming_patterns": [
    "buyer_po", "style_master", "cut_plan", "order_breakdown"
  ],
  
  "workflow_signals": [
    "Orders broken down by: style × color × size",
    "BOMs specific to: style-color-size combination",
    "Common columns: size_breakdown, color_ratio, pack_ratio"
  ],
  
  "key_doctypes": ["Item", "Customer", "BOM", "Work Order", "Sales Order"],
  
  "bottlenecks": [
    "Size/color variant explosion",
    "Fabric wastage tracking",
    "Style-wise BOM management"
  ]
}
```

**Example 2**: Chemical Batch Manufacturing
```json
{
  "f3iche_id": "chemical_batch_pharma",
  "industry": "chemical",
  "business_model": "batch manufacturing with quality control",
  "customer_segment": "pharma ingredients, specialty chemicals",
  
  "terminology_patterns": {
    "items": ["formulation_id", "batch_code", "sku", "product_code"],
    "customers": ["distributor", "wholesaler", "end_user"],
    "manufacturing": ["recipe", "mix_ratio", "formula", "composition"],
    "quality": ["lot_number", "batch_lot", "test_report"]
  },
  
  "file_naming_patterns": [
    "formulation", "batch_plan", "production_schedule", "quality_log"
  ],
  
  "workflow_signals": [
    "Batch tracking is critical",
    "Shelf life and expiry dates mandatory",
    "Quality certificates per batch"
  ],
  
  "key_doctypes": ["Item", "BOM", "Batch", "Work Order", "Quality Inspection"],
  
  "bottlenecks": [
    "Batch traceability",
    "Quality gate before sale",
    "Shelf life management"
  ]
}
```

**Total F3iches needed**: 50-100 (not 5)

**Maintenance**: Research team adds 1-2 per month as new verticals onboard

---

## Layer 1: Company Knowledge Space

### Concept: Learn from Customer's Own Data

**When company uploads first 3-5 files**:

```python
class CompanyKnowledgeSpace:
    """Per-project learning layer"""
    
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.f3iche = None  # Set during discovery
        self.observed_terms = {}  # Learns over time
        self.embedding_space = None  # Company-specific vectors
    
    async def learn_from_uploads(self, files: List[UploadedFile]):
        """Extract company's terminology from initial uploads"""
        
        # 1. Extract ALL unique columns
        all_columns = set()
        for file in files:
            columns = extract_columns(file)
            all_columns.update(columns)
        
        # 2. Extract ALL filenames
        filenames = [f.name for f in files]
        
        # 3. Extract sample data patterns
        samples = []
        for file in files:
            sample_rows = read_first_10_rows(file)
            samples.append({
                "filename": file.name,
                "columns": columns,
                "sample": sample_rows
            })
        
        # 4. Build company-specific context
        company_context = f"""
Company ID: {self.project_id}
F3iche: {self.f3iche}

Terminology observed:
- Column names: {sorted(all_columns)}
- File names: {filenames}

Sample data:
{json.dumps(samples, indent=2)}

This company's specific terminology should be learned for future mappings.
        """
        
        # 5. Embed company context into separate vector space
        self.embedding_space = await embed_company_context(
            context=company_context,
            namespace=f"company_{project_id}"
        )
        
        logger.info(
            "Learned company terminology: %d unique columns, %d files",
            len(all_columns), len(files)
        )
    
    async def infer_field_mapping(
        self, 
        column_name: str, 
        doctype: str,
        file_context: str
    ) -> Optional[str]:
        """Infer what ERPNext field this column maps to"""
        
        # Step 1: Check if we've seen this exact column before
        cache_key = f"{doctype}::{column_name}"
        if cache_key in self.observed_terms:
            return self.observed_terms[cache_key]
        
        # Step 2: Search company-specific embeddings
        query = f"""
In {self.f3iche} context, for {doctype} doctype:
What ERPNext field does column '{column_name}' map to?

Context: {file_context}
        """
        
        results = await search_embeddings(
            query=query,
            namespace=f"company_{self.project_id}",
            top_k=3
        )
        
        if results and results[0].score > 0.85:
            # High confidence from company's own data
            field = results[0].metadata["field"]
            self.observed_terms[cache_key] = field
            return field
        
        # Step 3: Fall back to F3iche-level embeddings
        results = await search_embeddings(
            query=query,
            namespace=f"f3iche_{self.f3iche}",
            top_k=3
        )
        
        if results and results[0].score > 0.75:
            field = results[0].metadata["field"]
            self.observed_terms[cache_key] = field
            return field
        
        # Step 4: Return None → triggers Layer 3 (LLM inference)
        return None
```

**Key Innovation**: Each company has its OWN embedding space. "style_code" means different things to different companies.

---

## Layer 2: Live ERP Schema (Already Built!)

### Make Live Schema PRIMARY (Not Fallback)

**Current flow**:
```python
# Step 1: Try to load mapping/*.json
kb_fields = load_kb_mapping(doctype)

# Step 2: If KB miss, try live schema
if not kb_fields:
    live_fields = await fetch_live_doctype_schema(doctype, project_id)
```

**New flow**:
```python
# Step 1: ALWAYS fetch live schema first (it's authoritative)
live_fields = await fetch_live_doctype_schema(doctype, project_id)

# Step 2: Enrich with F3iche-specific context (not manual synonyms)
enriched = await enrich_with_f3iche_context(
    live_fields, 
    f3iche=company.f3iche
)

# Step 3: No KB file needed!
```

**Benefits**:
- Works for ANY doctype (even custom ones customer added)
- Always up-to-date (reflects customer's actual ERP)
- Zero maintenance (no 148 JSON files)
- Automatic synonym generation (fieldname + label)

**Already implemented**: Yes! (`live_schema.py`, 207 lines)

---

## Layer 3: LLM Inference Engine

### Doctype Classification

**Current**: Manual rules in `filename_priors.json` + `column_priors.json`

**New**: LLM with multi-source context

```python
async def classify_doctype_llm(
    filename: str,
    columns: List[str],
    sample_rows: List[Dict],
    company: CompanyKnowledgeSpace,
    available_doctypes: List[str]
) -> Tuple[str, float]:
    """
    Infer doctype using LLM with rich context.
    
    Returns: (doctype, confidence_score)
    """
    
    # Build rich context
    f3iche_def = load_f3iche(company.f3iche)
    
    prompt = f"""You are an ERP data specialist analyzing a user's uploaded file.

COMPANY CONTEXT:
- Industry: {f3iche_def["industry"]}
- Business model: {f3iche_def["business_model"]}
- F3iche: {company.f3iche}

F3ICHE TYPICAL TERMINOLOGY:
{json.dumps(f3iche_def["terminology_patterns"], indent=2)}

FILE DETAILS:
- Filename: {filename}
- Columns: {columns}
- Sample rows (first 3):
{json.dumps(sample_rows[:3], indent=2)}

AVAILABLE DOCTYPES:
{available_doctypes}

TASK:
Determine which ERPNext doctype this file represents.

REASONING:
1. Look at filename patterns from F3iche
2. Match columns to typical terminology
3. Check sample data values
4. Consider business workflow

Return JSON:
{{
  "doctype": "exact doctype name from available list",
  "confidence": 0.0 to 1.0,
  "reasoning": "why you chose this doctype"
}}

If filename is "style_master.csv" with columns like "style_code", "buyer_name", 
it's likely Item (in garment context, style = item).

If filename is "order_breakdown.xlsx" with "po_number", "item_code", "qty",
it's likely Sales Order.
    """
    
    response = await llm.generate_json(prompt, temperature=0.1)
    
    return response["doctype"], response["confidence"]
```

**Cost**: ~$0.002 per file  
**Accuracy**: 90-95% (better than manual rules at 85%)  
**Maintenance**: Zero (scales to infinite companies)

---

### Column Mapping

**Current**: Manual synonyms in 148 `mapping/*.json` files

**New**: LLM with live schema + company context

```python
async def map_columns_llm(
    columns: List[str],
    doctype: str,
    live_schema: List[Dict],
    company: CompanyKnowledgeSpace,
    sample_data: Dict
) -> Dict[str, str]:
    """
    Map user columns to ERPNext fields using LLM.
    
    Returns: {user_column: erp_field}
    """
    
    # Try company-specific learning first (Layer 1)
    mappings = {}
    unmapped = []
    
    for col in columns:
        field = await company.infer_field_mapping(col, doctype, sample_data)
        if field:
            mappings[col] = field
        else:
            unmapped.append(col)
    
    # If some columns still unmapped, use LLM (Layer 3)
    if unmapped:
        f3iche_def = load_f3iche(company.f3iche)
        field_options = [f["fieldname"] for f in live_schema]
        
        prompt = f"""You are mapping user column names to ERPNext field names.

CONTEXT:
- Doctype: {doctype}
- F3iche: {company.f3iche} ({f3iche_def["industry"]} - {f3iche_def["business_model"]})

F3ICHE TERMINOLOGY HINTS:
{json.dumps(f3iche_def["terminology_patterns"], indent=2)}

USER COLUMNS TO MAP:
{unmapped}

AVAILABLE ERPNext FIELDS:
{field_options}

SAMPLE DATA:
{json.dumps(sample_data, indent=2)}

TASK:
For each user column, determine the best matching ERPNext field.

RULES:
1. Use F3iche terminology hints (e.g., "style_code" → "item_code" in garment)
2. Consider field types (date columns → date fields)
3. Look at sample values for clues
4. If no good match, return null

Return JSON:
{{
  "user_column_1": "erp_field_name" or null,
  "user_column_2": "erp_field_name" or null,
  ...
}}
        """
        
        llm_mappings = await llm.generate_json(prompt, temperature=0.1)
        
        # Merge LLM mappings
        for col, field in llm_mappings.items():
            if field:
                mappings[col] = field
                
                # Remember for next file from this company
                await company.remember_mapping(col, doctype, field)
    
    return mappings
```

**Key Innovation**: 
- Uses company's learned terminology (Layer 1)
- Uses F3iche context (Layer 0)
- Uses live schema (Layer 2)
- Only calls LLM when needed (cost-efficient)

---

## Layer 4: Feedback Loop (Future)

### After 100 Customers: Fine-Tune Model

**Concept**: Collect successful mappings, fine-tune GPT on F3Next-specific patterns

```python
# Collect training data
training_data = []

for project in successful_projects:
    for file in project.uploaded_files:
        training_data.append({
            "input": {
                "filename": file.name,
                "columns": file.columns,
                "f3iche": project.f3iche,
                "sample": file.sample_rows
            },
            "output": {
                "doctype": file.classified_as,
                "mappings": file.field_mappings
            }
        })

# Fine-tune GPT-4 on F3Next patterns
fine_tuned_model = await openai.fine_tune(
    base_model="gpt-4o",
    training_data=training_data,
    epochs=3
)

# Deploy fine-tuned model
# Accuracy improves from 90% → 95%+
# Cost per inference drops from $0.002 → $0.0005
```

**When to do this**: After 100 successful customer implementations  
**Cost**: ~$5K-10K one-time  
**Benefit**: 5% accuracy improvement, 75% cost reduction  
**Required for v1?**: No (nice-to-have for scale)

---

## What Gets Deleted

### Files to DELETE (152 files)

| File | Why Delete | Replacement |
|------|-----------|-------------|
| `mapping/*.json` (148 files) | 90% duplicate of live schema | Layer 2 (live schema) |
| `filename_priors.json` | Manual rules don't scale | Layer 3 (LLM inference) |
| `column_priors.json` | Manual rules don't scale | Layer 3 (LLM inference) |
| `merge_policies.json` | Business logic in JSON | Move to Python code |
| `party_entity_rules.json` | Business logic in JSON | Move to Python code |

**Total deleted**: 152 files

---

### Files to KEEP (6 files)

| File | Owner | Purpose |
|------|-------|---------|
| `erpnext_doctype_graph.json` | Research | Canonical doctype dependencies |
| `signals_registry.json` | Research | F3iche niche scoring (simplified) |
| F3iche JSONs (4 → 50-100) | Research | Narrow business model definitions |
| Embedding corpus (NEW) | Research | ~70 universal concept docs |

---

## What Gets Created

### New: Embedding Corpus

**Structure**:
```
containers/knowledge_base/common/concepts/
├── universal/
│   ├── party_entity.md          # Customer/Supplier concept
│   ├── item_product.md          # Item/Product concept
│   ├── transaction_document.md  # Orders/Invoices concept
│   └── ... (~20 universal docs)
│
└── f3iche_specific/
    ├── garment_terminology.md   # Garment-specific terms
    ├── chemical_terminology.md  # Chemical-specific terms
    └── ... (~50 F3iche-specific docs)
```

**Example: party_entity.md**
```markdown
# Party Entity (Universal ERP Concept)

## Definition
A business entity you trade with - someone you sell to or buy from.

## ERP Variants
- **ERPNext**: Customer (buying from you), Supplier (selling to you)
- **SAP**: Business Partner (BP) - single entity for both
- **Odoo**: res.partner - single model with type flag

## Common User Terms
- Customer side: client, buyer, customer, account, party, retailer, brand, distributor
- Supplier side: vendor, supplier, seller, wholesaler, manufacturer

## Typical Column Names
- Identity: party_name, customer_name, client_name, ledger_name, account_name, buyer_code
- Code: party_code, customer_id, client_id, account_no
- Category: customer_group, party_type, segment

## File Naming Patterns
- Customer: clients, customers, parties, accounts, buyers, ledger
- Supplier: vendors, suppliers, sellers

## Industry Variations

### Garment Manufacturing
- Customers often called: buyer, brand, importer
- Suppliers often called: fabric_supplier, trim_vendor

### Chemical Industry  
- Customers often called: distributor, end_user, wholesaler
- Suppliers often called: raw_material_supplier, ingredient_vendor

### Job Shop
- Customers often called: client, account, project_owner
- Suppliers often called: material_supplier, subcontractor
```

**Total docs**: ~70 (not 800!)

---

## Summary: Before vs After

| Aspect | Current (Broken) | Proposed (Scalable) |
|--------|-----------------|---------------------|
| **Doctype inference** | Manual rules (230 lines) | LLM + F3iche context |
| **Field mapping** | 148 manual files | Live schema + LLM |
| **Company variations** | Patch per customer | Learn from uploads |
| **New customer** | Add entries, restart worker | Zero changes |
| **New doctype** | 3-4 hours manual work | Zero work (live API) |
| **New F3iche** | Weeks of synonym writing | 1 JSON + 2-3 docs |
| **Scale limit** | ~15 doctypes, ~5 customers | 800 doctypes, 1000+ customers |
| **Accuracy** | 85% (manual rules) | 90-95% (LLM + learning) |
| **Cost per file** | Developer time | $0.002 LLM cost |

---

**Next**: See `03_KB_STRUCTURE.md` for detailed file organization
