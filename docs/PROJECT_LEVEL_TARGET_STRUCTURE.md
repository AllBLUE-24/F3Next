# Project-Level Target Structure Architecture

## Overview

Target structure and MVP boundary generation has been moved from **IS workflow** (corpus-dependent) to **Discovery completion** (corpus-independent). This architectural change makes these artifacts reusable across multiple IS runs if the f3iche and bottleneck remain the same.

## Key Changes

### Before (Old Architecture)
- Target structure generated **during IS workflow Step 8**
- **Corpus-dependent**: Used uploaded files to determine seeds
- Stored at **session level** (`is_target_structures` table)
- **Regenerated** for every IS run
- Mix of f3iche template + file-based inference
- Result: Different target structures for same bottleneck with different files

### After (New Architecture)
- Target structure generated **post-discovery** (after "Proceed to Implementation" button click)
- **Corpus-independent**: Based only on f3iche template + discovery chat
- Stored at **project level** (`project_target_structures`, `project_mvp_boundaries` tables)
- **Reusable** across IS runs
- Pure f3iche template-driven (optional LLM enhancement from discovery context)
- Result: Consistent target structure for same bottleneck, regardless of corpus

## Flow Diagram

```
Discovery Chat → Complete Discovery → Recommendation Page
                                           ↓
                                    [Proceed to Implementation] ← User clicks
                                           ↓
                         POST /api/discovery/{project_id}/proceed-to-implementation
                                           ↓
                              generate_project_target_structure()
                                           ↓
                    ┌─────────────────────┴─────────────────────┐
                    ↓                                             ↓
        project_target_structures                    project_mvp_boundaries
         (all doctypes + steps)                       (seeds only + scope)
                    ↓                                             ↓
                    └─────────────────────┬─────────────────────┘
                                          ↓
                                    Store in R2:
                         target_structure.json, mvp_boundary.json
                                          ↓
                                   Upload Page → IS Workflow
                                          ↓
                        load_project_target_structure() (Step 8)
                                          ↓
                            Use pre-generated target (no generation!)
```

## Database Schema

### `project_target_structures`
Stores complete target structure at **project level**:

```sql
CREATE TABLE project_target_structures (
    id UUID PRIMARY KEY,
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    f3iche VARCHAR NOT NULL,
    discovery_bottleneck TEXT,
    llm_enhanced BOOLEAN DEFAULT false,
    llm_reasoning TEXT,
    total_doctypes INTEGER,
    total_seed_doctypes INTEGER,
    total_setup_steps INTEGER,
    r2_target_path VARCHAR,     -- Full target structure JSON
    r2_mvp_path VARCHAR,         -- MVP boundary JSON
    seed_doctypes JSONB,         -- MVP seeds
    required_doctypes JSONB,     -- All doctypes (seeds + prereqs)
    setup_steps JSONB,           -- Ordered setup actions
    import_phases JSONB,         -- Phase groupings
    validation_rules JSONB,      -- F3iche-specific rules
    mvp_focus JSONB,             -- From discovery
    deferred_doctypes JSONB,     -- Empty for corpus-independent
    corpus_independent BOOLEAN DEFAULT true,
    graph_driven BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### `project_mvp_boundaries`
Stores MVP scope at **project level** (separate for clarity):

```sql
CREATE TABLE project_mvp_boundaries (
    id UUID PRIMARY KEY,
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE UNIQUE,
    f3iche VARCHAR NOT NULL,
    primary_bottleneck TEXT,
    functional_requirements JSONB,  -- From discovery
    seed_doctypes JSONB,            -- What's in MVP
    deferred_doctypes JSONB,        -- What's deferred (empty for now)
    mode VARCHAR DEFAULT 'f3iche_template',
    llm_enhanced BOOLEAN DEFAULT false,
    llm_reasoning TEXT,
    r2_path VARCHAR,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

## Benefits

### 1. Corpus Independence
- Target structure no longer depends on uploaded files
- Same f3iche + bottleneck = same target structure
- Predictable, testable, analyzable

### 2. Reusability
- Generate once post-discovery
- Reuse across multiple IS runs
- No regeneration overhead

### 3. Simple Gap Analysis
```
Gap = corpus_doctypes - mvp_boundary_doctypes
```
Now you can see exactly what's missing without complex inference.

### 4. Better Supervisor Messages
- MVP boundary is constant for a given bottleneck
- Supervisor can show: "You're missing doctypes X, Y, Z for this MVP"
- Messages are deterministic and testable

### 5. Separation of Concerns
- **Discovery**: Understands business needs → generates target
- **Implementation**: Maps corpus → fills target
- Clean boundary between stages

## API Endpoints

### Generate Target Structure (POST)
```
POST /api/discovery/{project_id}/proceed-to-implementation
```

**When**: User clicks "Proceed to Implementation" on recommendation page

**Returns**:
```json
{
  "status": "success",
  "message": "Target structure and MVP boundary generated successfully",
  "data": {
    "target_structure_id": "uuid",
    "mvp_boundary_id": "uuid",
    "seed_doctypes": ["Production Plan", "Stock Entry"],
    "required_doctypes": ["Company", "UOM", "Warehouse", "Item Group", "Item", "Stock Entry", "Production Plan"],
    "total_doctypes": 7,
    "total_seeds": 2,
    "r2_target_path": "strahats/project_{id}/_discovery/target_structure.json",
    "r2_mvp_path": "strahats/project_{id}/_discovery/mvp_boundary.json",
    "f3iche": "manufacturing"
  }
}
```

## Frontend Changes

### Recommendation Page Button
```typescript
const handleProceedToImplementation = async () => {
  setIsGenerating(true);
  
  // Generate target structure + MVP boundary
  await fetch(`${apiUrl}/api/discovery/${projectId}/proceed-to-implementation`, {
    method: "POST"
  });
  
  // Then navigate to upload page
  router.push(`/${companySlug}/${userSlug}/upload?projectId=${projectId}`);
};
```

## Backward Compatibility

### Legacy Fallback
The IS workflow includes a **legacy fallback** for old projects created before this change:

```python
# Try project-level first (new flow)
target = await load_project_target_structure(session_id)

if not target.get("exists"):
    # Fallback to old corpus-dependent generation
    target = await build_target_structure(corpus_understanding, ...)
```

Old projects will continue to work but won't get the benefits of corpus-independence.

## Testing

### Test Case 1: Same Bottleneck, Different Files
**Setup**:
1. Complete discovery with f3iche=manufacturing, bottleneck="WIP visibility"
2. Proceed to implementation (generates target)
3. Upload files A, B, C → Run IS
4. Later: Upload different files X, Y, Z → Run IS again

**Expected**:
- Both IS runs use **same target structure**
- Both IS runs use **same MVP boundary**
- Gap analysis is: `{X, Y, Z} - {Production Plan, Stock Entry}`

### Test Case 2: Fresh Project
**Setup**:
1. Complete discovery
2. Click "Proceed to Implementation"

**Expected**:
- `project_target_structures` row created
- `project_mvp_boundaries` row created
- R2 files created:
  - `{company_slug}/project_{id}/_discovery/target_structure.json`
  - `{company_slug}/project_{id}/_discovery/mvp_boundary.json`

### Test Case 3: IS Workflow Loads Correctly
**Setup**:
1. Generate target structure (Test Case 2)
2. Start IS workflow

**Expected**:
- Step 8 loads from `project_target_structures` (not generates)
- Log shows: `source=project_level (corpus-independent)`
- No corpus-dependent logic runs

## Migration Guide

### Run Migration
```bash
cd shared/alembic
alembic upgrade head
```

This creates the two new tables.

### Update Existing Projects (Optional)
For existing projects with discovery complete but no project-level target:

```python
from containers.implementation.target_agent.post_discovery_service import (
    generate_project_target_structure
)

# For each project with discovery_metadata:
await generate_project_target_structure(
    db=db,
    project_id=project.id,
    company_slug=project.company_slug
)
```

## Future Enhancements

1. **LLM Enhancement**: Use discovery chat to extract company-specific doctypes beyond f3iche template
2. **Template Versioning**: Track f3iche template versions over time
3. **Target Diff Tool**: Show what changed between target structures for debugging
4. **Supervisor Integration**: Use project-level target for deterministic prompts

## Related Files

### Core Implementation
- `shared/models/project_target.py` - New models
- `containers/implementation/target_agent/build_post_discovery.py` - Generation logic
- `containers/implementation/target_agent/post_discovery_service.py` - Service layer
- `containers/implementation/file_io/load_project_target_structure.py` - Loader activity

### API
- `backend/app/api/discovery.py` - New endpoint

### Frontend
- `frontend/src/app/[companySlug]/[userSlug]/recommendation/page.tsx` - Button handler

### Workflow
- `containers/implementation/is_workflow/workflow.py` - Step 8 updated
- `containers/implementation/is_worker.py` - Activity registration

### Database
- `shared/alembic/versions/add_project_level_target_structures.py` - Migration

## Questions?

Contact the architecture team or refer to:
- `docs/FOUNDATIONS.md` - Overall F3Next architecture
- `docs/IS_V2_BACKLOG.md` - IS system design
