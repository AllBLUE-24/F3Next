# Implementation Plan - Week by Week

> **Duration**: 8-10 weeks (2-3 months)  
> **Team**: 1-2 senior engineers + research team  
> **Risk**: High (5th restart), but foundation is correct

---

## Pre-Requisites

**Before starting**:
1. ✅ Decision made to rebuild (see `06_DECISION_FRAMEWORK.md`)
2. ✅ Current code deployed to staging (fallback if needed)
3. ✅ Team aligned on scope and timeline
4. ✅ Runway check (can afford 2-3 month delay?)

**Branch strategy**:
```bash
# Create reform branch
git checkout -b feature/v1-architecture-reform
git push -u origin feature/v1-architecture-reform

# Work here for 8-10 weeks
# Merge to main only when complete
```

---

## Week 1: Foundation - KB Structure

### Goals
- Create new KB directory structure
- Write initial concept docs
- Split F3iches from 5 broad → 15-30 narrow

### Tasks

**Day 1-2: Create Directory Structure**
```bash
# Create new directories
mkdir -p containers/knowledge_base/common/concepts/universal
mkdir -p containers/knowledge_base/common/concepts/f3iche_specific
mkdir -p containers/knowledge_base/common/f3iches

# Keep existing
# containers/knowledge_base/erpnext/erpnext_doctype_graph.json ✅
# containers/knowledge_base/common/signals_registry.json ✅
```

**Day 2-3: Write Universal Concept Docs**

Research team writes 20 docs:
- party_entity.md
- item_product.md
- transaction_document.md
- financial_posting.md
- inventory_movement.md
- manufacturing_order.md
- quality_control.md
- batch_lot.md
- serial_number.md
- price_list.md
- payment_entry.md
- journal_entry.md
- tax_template.md
- warehouse_location.md
- uom_unit.md
- currency_exchange.md
- territory_geography.md
- department_cost_center.md
- project_job.md
- timesheet_attendance.md

**Template**: See `03_KB_STRUCTURE.md` for format

**Day 4-5: Split F3iches**

Research team splits current F3iches:

**Current**:
- manufacturing_garment_variants.json → Split into 5-7

**New**:
- garment_mto_export_b2b.json
- garment_wholesale_domestic.json
- garment_retail_chain.json
- garment_fabric_manufacturing.json
- garment_home_textiles.json

**Repeat for**:
- Chemical (5-7 F3iches)
- Job shop (5-7 F3iches)
- Food (3-5 F3iches)

**Total**: 15-30 narrow F3iches by week end

### Deliverables (Week 1)
- [ ] 20 universal concept docs written
- [ ] 15-30 narrow F3iche JSONs created
- [ ] Directory structure set up
- [ ] All files reviewed by team

**Checkpoint**: Review session Friday - does KB structure make sense?

---

## Week 2: Embedding Pipeline

### Goals
- Set up vector DB (Pinecone/Qdrant/Weaviate)
- Build embedding pipeline
- Embed all concept docs + F3iches
- Test semantic search

### Tasks

**Day 1: Choose Vector DB**

Options:
1. **Pinecone** (managed, $70/mo, easy)
2. **Qdrant** (self-hosted, free, Docker)
3. **Weaviate** (self-hosted, free, Docker)

**Recommendation**: Qdrant (self-hosted, no vendor lock-in)

```bash
# Add to docker-compose.yml
qdrant:
  image: qdrant/qdrant:latest
  ports:
    - "6333:6333"
  volumes:
    - ./qdrant_storage:/qdrant/storage
```

**Day 2: Build Embedding Module**

```python
# shared/embeddings.py

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from openai import AsyncOpenAI

client = QdrantClient(url="http://localhost:6333")
openai_client = AsyncOpenAI()

async def embed_text(text: str) -> List[float]:
    """Embed text using OpenAI text-embedding-3-small"""
    response = await openai_client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding

async def create_collection(name: str):
    """Create Qdrant collection"""
    client.create_collection(
        collection_name=name,
        vectors_config=VectorParams(size=1536, distance=Distance.COSINE)
    )

async def upsert_embedding(
    collection: str,
    id: str,
    text: str,
    metadata: Dict
):
    """Embed and store text"""
    vector = await embed_text(text)
    client.upsert(
        collection_name=collection,
        points=[PointStruct(
            id=id,
            vector=vector,
            payload=metadata
        )]
    )

async def search_embeddings(
    collection: str,
    query: str,
    top_k: int = 5
) -> List[Dict]:
    """Search similar texts"""
    query_vector = await embed_text(query)
    results = client.search(
        collection_name=collection,
        query_vector=query_vector,
        limit=top_k
    )
    return [
        {
            "text": r.payload.get("text"),
            "metadata": r.payload,
            "score": r.score
        }
        for r in results
    ]
```

**Day 3-4: Embed Concept Docs**

```python
# scripts/embed_kb.py

async def embed_concept_docs():
    """Embed all concept docs into universal_concepts collection"""
    
    await create_collection("universal_concepts")
    
    concept_dir = Path("containers/knowledge_base/common/concepts/universal")
    
    for md_file in concept_dir.glob("*.md"):
        content = md_file.read_text()
        
        # Chunk by sections (split on ## headers)
        chunks = split_markdown_by_sections(content)
        
        for i, chunk in enumerate(chunks):
            await upsert_embedding(
                collection="universal_concepts",
                id=f"{md_file.stem}_{i}",
                text=chunk,
                metadata={
                    "file": md_file.name,
                    "section": i,
                    "type": "universal_concept"
                }
            )
    
    print(f"Embedded {len(chunks)} chunks from {len(list(concept_dir.glob('*.md')))} files")

async def embed_f3iches():
    """Embed all F3iche JSONs"""
    
    await create_collection("f3iche_registry")
    
    f3iche_dir = Path("containers/knowledge_base/common/f3iches")
    
    for json_file in f3iche_dir.glob("*.json"):
        data = json.loads(json_file.read_text())
        
        # Embed entire F3iche as single document
        text = json.dumps(data, indent=2)
        
        await upsert_embedding(
            collection="f3iche_registry",
            id=data["f3iche_id"],
            text=text,
            metadata={
                "f3iche_id": data["f3iche_id"],
                "industry": data["classification"]["industry"],
                "business_model": data["classification"]["business_model"],
                **data
            }
        )
    
    print(f"Embedded {len(list(f3iche_dir.glob('*.json')))} F3iches")

# Run embedding
asyncio.run(embed_concept_docs())
asyncio.run(embed_f3iches())
```

**Day 5: Test Semantic Search**

```python
# Test queries
queries = [
    "What is a customer in ERP?",
    "How do garment manufacturers name their items?",
    "What does 'style_code' mean in manufacturing?",
    "What is a party entity?",
]

for query in queries:
    results = await search_embeddings("universal_concepts", query, top_k=3)
    print(f"\nQuery: {query}")
    for r in results:
        print(f"  Score: {r['score']:.3f} | {r['metadata']['file']}")
```

### Deliverables (Week 2)
- [ ] Vector DB running
- [ ] Embedding module written
- [ ] All concept docs embedded
- [ ] All F3iches embedded
- [ ] Search tests passing

**Checkpoint**: Can we find relevant docs by semantic search?

---

## Week 3: Company Learning Layer

### Goals
- Build company knowledge space DB table
- Implement company-specific embedding namespaces
- Build learning-from-uploads module
- Test with mock data

### Tasks

**Day 1: Database Schema**

```sql
-- Add to migrations
CREATE TABLE is_company_knowledge (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id),
    f3iche VARCHAR(100),
    learned_terms JSONB DEFAULT '{}',
    observed_columns TEXT[] DEFAULT '{}',
    observed_filenames TEXT[] DEFAULT '{}',
    embedding_namespace VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_company_knowledge_project ON is_company_knowledge(project_id);
```

**Day 2-3: Company Learning Module**

```python
# containers/implementation/company_learning/knowledge_space.py

class CompanyKnowledgeSpace:
    """Learns from company's own data"""
    
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.f3iche = None
        self.namespace = f"company_{project_id}"
    
    async def initialize(self, f3iche: str):
        """Set up company knowledge space"""
        self.f3iche = f3iche
        
        # Create Qdrant collection for this company
        await create_collection(self.namespace)
        
        # Insert DB record
        async with AsyncSessionLocal() as db:
            knowledge = ISCompanyKnowledge(
                project_id=uuid.UUID(self.project_id),
                f3iche=f3iche,
                embedding_namespace=self.namespace
            )
            db.add(knowledge)
            await db.commit()
    
    async def learn_from_uploads(self, files: List[Dict]):
        """Extract and learn company terminology"""
        
        # Extract all unique columns
        all_columns = set()
        for file in files:
            cols = file.get("columns", [])
            all_columns.update(cols)
        
        # Extract filenames
        filenames = [f.get("name", "") for f in files]
        
        # Build company context
        context = self._build_context(all_columns, filenames, files)
        
        # Embed context
        await upsert_embedding(
            collection=self.namespace,
            id="company_context",
            text=context,
            metadata={
                "type": "company_context",
                "columns": list(all_columns),
                "filenames": filenames
            }
        )
        
        # Update DB
        await self._update_observed_terms(all_columns, filenames)
        
        logger.info(
            "Company learning: %d columns, %d files observed",
            len(all_columns), len(files)
        )
    
    async def infer_field_mapping(
        self, 
        column: str, 
        doctype: str,
        file_context: str
    ) -> Optional[str]:
        """Infer ERPNext field for user column"""
        
        # Check cache first
        cached = await self._get_cached_mapping(column, doctype)
        if cached:
            return cached
        
        # Search company embeddings
        query = f"For {doctype}, what field does '{column}' map to?"
        results = await search_embeddings(
            collection=self.namespace,
            query=query,
            top_k=3
        )
        
        if results and results[0]["score"] > 0.85:
            field = results[0]["metadata"].get("field")
            await self._cache_mapping(column, doctype, field)
            return field
        
        # No high-confidence match
        return None
    
    async def remember_mapping(
        self,
        column: str,
        doctype: str,
        field: str
    ):
        """Remember successful mapping for next time"""
        
        # Store in DB cache
        async with AsyncSessionLocal() as db:
            knowledge = await db.execute(
                select(ISCompanyKnowledge)
                .where(ISCompanyKnowledge.project_id == self.project_id)
            )
            knowledge = knowledge.scalar_one_or_none()
            
            if knowledge:
                learned = dict(knowledge.learned_terms or {})
                learned[f"{doctype}::{column}"] = field
                knowledge.learned_terms = learned
                knowledge.updated_at = datetime.utcnow()
                await db.commit()
        
        # Embed mapping
        await upsert_embedding(
            collection=self.namespace,
            id=f"mapping_{doctype}_{column}",
            text=f"Column '{column}' maps to field '{field}' in {doctype}",
            metadata={
                "type": "mapping",
                "column": column,
                "doctype": doctype,
                "field": field
            }
        )
```

**Day 4-5: Integration + Tests**

```python
# Test with mock company data
async def test_company_learning():
    # Create company
    company = CompanyKnowledgeSpace("test_project_123")
    await company.initialize("garment_mto_export_b2b")
    
    # Mock uploads
    files = [
        {
            "name": "buyer_po.xlsx",
            "columns": ["buyer_name", "style_code", "po_ref", "color", "size"]
        },
        {
            "name": "style_master.csv",
            "columns": ["style_code", "description", "fabric", "price"]
        }
    ]
    
    # Learn
    await company.learn_from_uploads(files)
    
    # Test inference
    field = await company.infer_field_mapping(
        column="buyer_name",
        doctype="Customer",
        file_context="buyer_po.xlsx"
    )
    
    assert field == "customer_name" or field is None  # None is OK (falls back to LLM)
```

### Deliverables (Week 3)
- [ ] Company knowledge DB table
- [ ] Company learning module written
- [ ] Learning from uploads works
- [ ] Tests passing

**Checkpoint**: Can we learn and cache company-specific terms?

---

## Week 4: LLM Inference Engine

### Goals
- Build LLM-based doctype classifier
- Build LLM-based column mapper
- Integrate with company learning layer
- Test accuracy on real files

### Tasks

**Day 1-2: Doctype Classifier**

```python
# containers/implementation/llm_inference/classifier.py

async def classify_doctype_llm(
    filename: str,
    columns: List[str],
    sample_rows: List[Dict],
    f3iche_id: str,
    available_doctypes: List[str]
) -> Tuple[str, float, str]:
    """
    Classify file to doctype using LLM.
    
    Returns: (doctype, confidence, reasoning)
    """
    
    # Load F3iche context
    f3iche_results = await search_embeddings(
        collection="f3iche_registry",
        query=f3iche_id,
        top_k=1
    )
    f3iche_data = f3iche_results[0]["metadata"] if f3iche_results else {}
    
    # Build prompt
    prompt = f"""You are an ERP data specialist analyzing a user's uploaded file.

COMPANY CONTEXT:
- F3iche: {f3iche_id}
- Industry: {f3iche_data.get('industry', 'unknown')}
- Business Model: {f3iche_data.get('business_model', 'unknown')}

F3ICHE TERMINOLOGY PATTERNS:
{json.dumps(f3iche_data.get('terminology_patterns', {}), indent=2)}

FILE DETAILS:
- Filename: {filename}
- Columns: {columns}
- Sample rows (first 3):
{json.dumps(sample_rows[:3], indent=2)}

AVAILABLE DOCTYPES:
{available_doctypes}

TASK:
Determine which ERPNext doctype this file represents.

REASONING STEPS:
1. Check filename against F3iche file_naming_patterns
2. Match columns to F3iche terminology_patterns
3. Examine sample data values
4. Consider business workflow

Return JSON ONLY:
{{
  "doctype": "exact doctype name from available list",
  "confidence": 0.0 to 1.0,
  "reasoning": "brief explanation (1-2 sentences)"
}}
    """
    
    response = await llm_generate_json(
        prompt=prompt,
        model="gpt-4o",
        temperature=0.1
    )
    
    return (
        response["doctype"],
        float(response["confidence"]),
        response["reasoning"]
    )
```

**Day 3-4: Column Mapper**

```python
# containers/implementation/llm_inference/mapper.py

async def map_columns_llm(
    columns: List[str],
    doctype: str,
    live_schema: List[Dict],
    f3iche_id: str,
    sample_data: Dict,
    company: CompanyKnowledgeSpace
) -> Dict[str, str]:
    """
    Map user columns to ERPNext fields using LLM.
    
    Returns: {user_column: erp_field}
    """
    
    # Step 1: Try company-specific learning first
    mappings = {}
    unmapped = []
    
    for col in columns:
        field = await company.infer_field_mapping(
            column=col,
            doctype=doctype,
            file_context=sample_data
        )
        
        if field:
            mappings[col] = field
            logger.info("Company cache hit: %s → %s", col, field)
        else:
            unmapped.append(col)
    
    # Step 2: If all mapped, done!
    if not unmapped:
        return mappings
    
    # Step 3: Use LLM for unmapped columns
    field_options = [f["fieldname"] for f in live_schema]
    
    # Get F3iche context
    f3iche_results = await search_embeddings(
        collection="f3iche_registry",
        query=f3iche_id,
        top_k=1
    )
    f3iche_data = f3iche_results[0]["metadata"] if f3iche_results else {}
    
    prompt = f"""You are mapping user column names to ERPNext field names.

CONTEXT:
- Doctype: {doctype}
- F3iche: {f3iche_id}
- Industry: {f3iche_data.get('industry')}
- Business Model: {f3iche_data.get('business_model')}

F3ICHE TERMINOLOGY HINTS:
{json.dumps(f3iche_data.get('terminology_patterns', {}), indent=2)}

USER COLUMNS TO MAP:
{unmapped}

AVAILABLE ERPNext FIELDS:
{field_options}

SAMPLE DATA (first 3 rows):
{json.dumps(sample_data, indent=2)}

TASK:
For each user column, determine the best matching ERPNext field.

RULES:
1. Use F3iche terminology hints (e.g., "style_code" → "item_code" in garment)
2. Consider field types (date columns → date fields)
3. Look at sample values for clues
4. If no good match, return null

Return JSON ONLY:
{{
  "col1": "field_name" or null,
  "col2": "field_name" or null,
  ...
}}
    """
    
    llm_mappings = await llm_generate_json(
        prompt=prompt,
        model="gpt-4o",
        temperature=0.1
    )
    
    # Merge LLM mappings
    for col, field in llm_mappings.items():
        if field:
            mappings[col] = field
            
            # Remember for next time
            await company.remember_mapping(col, doctype, field)
    
    return mappings
```

**Day 5: Integration Tests**

```python
# Test with real Green Surface data
async def test_llm_inference():
    # Load Green Surface files
    files = load_green_surface_files()
    
    # Initialize company
    company = CompanyKnowledgeSpace("green_surface")
    await company.initialize("chemical_batch_pharma")
    await company.learn_from_uploads(files)
    
    # Test classification
    for file in files:
        doctype, confidence, reasoning = await classify_doctype_llm(
            filename=file["name"],
            columns=file["columns"],
            sample_rows=file["sample"],
            f3iche_id="chemical_batch_pharma",
            available_doctypes=["Item", "Customer", "Supplier", "BOM", "Work Order", ...]
        )
        
        print(f"\nFile: {file['name']}")
        print(f"Classified as: {doctype} ({confidence:.2%})")
        print(f"Reasoning: {reasoning}")
        
        # Test mapping
        live_schema = await fetch_live_doctype_schema(doctype, "green_surface")
        mappings = await map_columns_llm(
            columns=file["columns"],
            doctype=doctype,
            live_schema=live_schema,
            f3iche_id="chemical_batch_pharma",
            sample_data=file["sample"],
            company=company
        )
        
        print(f"Mappings: {mappings}")
```

### Deliverables (Week 4)
- [ ] LLM classifier working
- [ ] LLM mapper working
- [ ] Integration with company learning
- [ ] Tests on real data passing

**Checkpoint**: Accuracy check - 85%+ on Green Surface files?

---

## Week 5-6: Code Migration & Integration

### Goals
- Rewrite classifier.py to use new system
- Rewrite mapper activities to use new system
- Migrate business logic from JSON to Python
- Wire everything together

### Tasks

**Week 5, Day 1-2: Rewrite Classifier**

```python
# containers/implementation/mapping_agent/classifier.py

async def classify_doctype(
    filename: str,
    columns: List[str],
    sample_rows: List[Dict],
    project_id: str,
    f3iche_id: str
) -> Tuple[str, float]:
    """
    NEW: LLM-based classification with company learning.
    
    OLD: Manual rules from filename_priors.json + column_priors.json
    """
    
    # Load company knowledge
    company = await load_company_knowledge(project_id)
    
    # Get available doctypes from graph
    graph = load_doctype_graph()
    available_doctypes = list(graph["doctypes"].keys())
    
    # Classify using LLM
    doctype, confidence, reasoning = await classify_doctype_llm(
        filename=filename,
        columns=columns,
        sample_rows=sample_rows,
        f3iche_id=f3iche_id or company.f3iche,
        available_doctypes=available_doctypes
    )
    
    logger.info(
        "Classified %s as %s (%.2%%) - %s",
        filename, doctype, confidence * 100, reasoning
    )
    
    return doctype, confidence
```

**Week 5, Day 3-5: Rewrite Mapper**

```python
# containers/implementation/mapping_agent/activities.py

@activity.defn
async def map_file_to_erpnext(input: MapFileInput) -> NodeStatusEnvelope:
    """
    NEW: Live schema + LLM + company learning
    
    OLD: Manual KB mapping files
    """
    
    # Load company knowledge
    company = await load_company_knowledge(input.project_id)
    
    # Classify doctype
    doctype, confidence = await classify_doctype(
        filename=input.filename,
        columns=input.columns,
        sample_rows=input.sample_rows,
        project_id=input.project_id,
        f3iche_id=company.f3iche
    )
    
    # Get live schema
    live_schema = await fetch_live_doctype_schema(
        doctype=doctype,
        project_id=input.project_id
    )
    
    # Map columns
    mappings = await map_columns_llm(
        columns=input.columns,
        doctype=doctype,
        live_schema=live_schema,
        f3iche_id=company.f3iche,
        sample_data=input.sample_rows,
        company=company
    )
    
    # Build mapped payload
    records = []
    for row in input.rows:
        record = {}
        for user_col, erp_field in mappings.items():
            if user_col in row:
                record[erp_field] = row[user_col]
        records.append(record)
    
    # Save to R2
    r2_key = await save_mapped_data(input.project_id, doctype, records, mappings)
    
    return NodeStatusEnvelope(
        ok=True,
        message=f"Mapped {len(records)} records to {doctype}",
        data={"r2_key": r2_key, "doctype": doctype, "mappings": mappings}
    )
```

**Week 6, Day 1-3: Migrate Business Logic**

```python
# containers/implementation/mapping_agent/corpus_merge.py

# OLD: Read merge_policies.json
# NEW: Python logic

def get_dedupe_key(doctype: str) -> Optional[str]:
    """
    Dedupe key per doctype.
    
    OLD: Read from merge_policies.json
    NEW: Hardcoded (simple, maintainable)
    """
    DEDUPE_KEYS = {
        "Customer": "customer_name",
        "Supplier": "supplier_name",
        "Item": "item_code",
        "BOM": "item",
        "Project": "project_name",
        "Work Order": "production_item",
    }
    return DEDUPE_KEYS.get(doctype)

# containers/implementation/is_common/entity_resolver.py

# OLD: Read party_entity_rules.json
# NEW: Python logic

def resolve_party_type(row: Dict, column_name: str) -> Optional[str]:
    """
    Determine if row is Customer or Supplier.
    
    OLD: Complex JSON rules
    NEW: Simple Python logic
    """
    value = str(row.get(column_name, "")).lower()
    
    # Customer indicators
    if any(kw in value for kw in ["customer", "client", "buyer"]):
        return "Customer"
    
    # Supplier indicators
    if any(kw in value for kw in ["supplier", "vendor", "seller"]):
        return "Supplier"
    
    # Default: Customer (B2B manufacturing context)
    return "Customer"
```

**Week 6, Day 4-5: Integration + Testing**

```python
# Test full flow
async def test_full_mapping_flow():
    # Upload files
    files = upload_green_surface_files()
    
    # Map each file
    for file in files:
        result = await map_file_to_erpnext(MapFileInput(
            project_id="green_surface",
            filename=file.name,
            columns=file.columns,
            rows=file.rows,
            sample_rows=file.rows[:10]
        ))
        
        assert result.ok
        print(f"Mapped {file.name} → {result.data['doctype']}")
```

### Deliverables (Week 5-6)
- [ ] Classifier rewritten
- [ ] Mapper rewritten
- [ ] Business logic migrated to Python
- [ ] Full flow integration tested
- [ ] Accuracy >= 85% on test files

**Checkpoint**: Can we map Green Surface files end-to-end?

---

## Week 7: Delete Old Code & Cleanup

### Goals
- Delete 152 KB patch files
- Update tests
- Clean up imports
- Documentation

### Tasks

**Day 1: Delete KB Files**

```bash
# AFTER confirming new code works!

# Delete manual mapping files (148 files)
rm -rf containers/knowledge_base/erpnext/schema/mapping/

# Delete manual classification rules
rm containers/knowledge_base/erpnext/schema/classification/filename_priors.json
rm containers/knowledge_base/erpnext/schema/classification/column_priors.json
rm containers/knowledge_base/erpnext/schema/classification/global_hints.json

# Delete business logic JSON files
rm containers/knowledge_base/erpnext/schema/corpus/merge_policies.json
rm containers/knowledge_base/erpnext/schema/corpus/party_entity_rules.json

# Delete entire schema folder
rm -rf containers/knowledge_base/erpnext/schema/

# Git commit
git add -A
git commit -m "refactor: delete 152 KB patch files, use LLM inference"
```

**Day 2-3: Update Tests**

```python
# Remove tests for old KB files
# Add tests for new LLM inference

# containers/implementation/tests/test_llm_classifier.py
# containers/implementation/tests/test_company_learning.py
# containers/implementation/tests/test_embedding_search.py
```

**Day 4: Clean Imports**

```python
# Remove all references to:
# - filename_priors()
# - column_priors()
# - load_kb_mapping()
# - merge_policies.json
# - party_entity_rules.json

# grep -r "filename_priors" --include="*.py"
# grep -r "column_priors" --include="*.py"
# grep -r "mapping\/*.json" --include="*.py"
```

**Day 5: Documentation**

```markdown
# Update docs
- README.md (new architecture overview)
- ARCH_IMPLEMENTATION.md (LLM inference layer)
- CONTRIBUTING.md (how to add new F3iche)
```

### Deliverables (Week 7)
- [ ] 152 KB files deleted
- [ ] Tests updated
- [ ] Imports cleaned
- [ ] Documentation updated

**Checkpoint**: Code compiles, tests pass, no broken imports?

---

## Week 8: Production Testing & Validation

### Goals
- Test with 3-5 different companies (mock data)
- Measure accuracy
- Tune prompts if needed
- Production deploy

### Tasks

**Day 1-2: Create Test Datasets**

```python
# Create mock datasets for:
# 1. Garment MTO Export
# 2. Chemical Batch Pharma
# 3. Job Shop Machining
# 4. Retail Chain
# 5. Food Processing

# Each with 5-10 files, varied terminology
```

**Day 3-4: Accuracy Testing**

```python
# Measure:
# - Doctype classification accuracy
# - Column mapping accuracy
# - False positive rate
# - Time per file

# Target: 90%+ accuracy
```

**Day 5: Production Deploy**

```bash
# Merge to main
git checkout main
git merge feature/v1-architecture-reform

# Deploy
docker-compose build
docker-compose up -d

# Restart workers
docker-compose restart implementation_worker
```

### Deliverables (Week 8)
- [ ] 5 test datasets validated
- [ ] Accuracy >= 90%
- [ ] Production deployed
- [ ] Monitoring in place

**Checkpoint**: Ready for first customer?

---

## Week 9-10: Buffer & Refinement

### Goals
- Fix any issues from Week 8
- Tune prompts based on accuracy
- Add more F3iches if needed
- Onboard first customer

### Tasks

**Flexible based on Week 8 results**

---

## Success Criteria (Final)

**Must achieve before considering complete**:

1. ✅ New customer upload = **0 code changes**
2. ✅ New customer upload = **0 KB file changes**
3. ✅ Mapping accuracy = **90%+ on first upload**
4. ✅ Mapping accuracy = **95%+ after 3 uploads**
5. ✅ Classification accuracy = **90%+**
6. ✅ Green Surface files map correctly
7. ✅ Tests passing (100% coverage on new modules)
8. ✅ Documentation complete

---

## Risk Mitigation

### If Accuracy < 90%

**Options**:
1. Tune LLM prompts (add more examples)
2. Enrich F3iche context (more terminology patterns)
3. Add more concept docs
4. Increase company learning sensitivity
5. Consider GPT-4o-mini → GPT-4o upgrade

### If Timeline Slips

**Options**:
1. Cut scope (focus on 15 F3iches, not 50)
2. Delay embeddings (use LLM without semantic search first)
3. Delay company learning (use LLM only)
4. Ship with lower accuracy (85%+)

### If Team Fatigue (5th Restart)

**Options**:
1. Pause, ship current code to 1 customer first
2. Split team (1 maintains old, 1 builds new)
3. Hire contractor for KB work
4. Reduce scope to MVP (10 F3iches)

---

## Estimated Costs

**Engineering time**: 8-10 weeks × 1 engineer = 2-3 months  
**LLM API costs**: ~$50-100 for testing + embedding  
**Vector DB**: $0 (self-hosted Qdrant)  
**Opportunity cost**: 2-3 months revenue delay

**Total**: ~$40K-60K in eng time + $50-100 API

---

**Next**: See `06_DECISION_FRAMEWORK.md` for ship vs rebuild analysis
