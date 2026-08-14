# P2: Move Target Structure Generation to Post-Discovery

## Problem Statement
Currently, target structure is generated in IS workflow Step 8 AFTER file upload, using corpus data to "defer" doctypes. This is backwards - we should define requirements BEFORE data collection.

## Architectural Change

### Current Flow (Wrong)
```
Discovery → Upload Files → IS Step 8: Generate Target (using corpus) → Step 5: Compare vs corpus → "You're missing files"
```

### New Flow (Correct)
```
Discovery → Generate Target (f3iche only) → Upload Files → IS Step 5: Compare vs target → "You're missing files"
```

## Implementation Plan

### Phase 1: Create Corpus-Independent Target Generator

**File**: `containers/implementation/target_agent/build_post_discovery.py`

Create new function that:
- Takes: `f3iche`, `mvp_focus`, `discovery_context` (optional chat for LLM enhancement)
- Returns: Target structure with `seed_doctypes`, `required_doctypes`, `setup_steps`, `import_phases`
- Does NOT use: `corpus_understanding`, `manifest`, `defer_without_evidence`
- Uses: `load_f3iche_template_seeds`, graph walking, validation rules

### Phase 2: Refactor Existing build_target_structure

**File**: `containers/implementation/target_agent/activities.py`

Modify `build_target_structure`:
- Remove calls to `seeds_from_corpus()` 
- Remove calls to `defer_without_evidence()`
- Use f3iche template as single source of truth for seeds
- Keep graph walking and structure generation
- Add comment: "Legacy activity - new sessions use post-discovery generation"

### Phase 3: Add Backend API Endpoint

**File**: `backend/app/api/target_structure.py`

New endpoint:
```python
@router.post("/generate-target")
async def generate_target_structure(request: GenerateTargetRequest):
    """
    Generate target structure after discovery (before file upload).
    Runs async - doesn't block user flow.
    """
    # Load discovery_metadata from hooks table
    # Call new build_post_discovery function
    # Save to is_target_structures + R2
    # Return status
```

### Phase 4: Update IS Workflow Step 8

**File**: `containers/implementation/is_workflow/workflow.py`

Change Step 8 logic:
```python
# Try to load pre-generated target
target = await _load_target_structure(session_id)

if not target:
    # Backward compatibility: generate now (old sessions)
    target = await build_target_structure(...)
else:
    # Target already exists from post-discovery generation
    logger.info("✓ Using pre-generated target structure")
```

### Phase 5: Add Frontend Trigger

**File**: `frontend/src/app/[companySlug]/[userSlug]/(Implementation)/upload/page.tsx`

Add server action:
```typescript
export async function ensureTargetStructure(projectId: string) {
  'use server';
  // Check if target exists
  // If not, trigger generation
  // Return status
}
```

In page component:
```typescript
useEffect(() => {
  ensureTargetStructure(projectId);
}, [projectId]);
```

### Phase 6: Update Data Readiness

**File**: `containers/implementation/data_readiness_agent/activities.py`

No changes needed - `_load_target_structure` already handles loading from DB.
Add better error handling if target structure is missing.

## Backward Compatibility Strategy

1. **Old sessions (pre-migration)**: Will not have target structure in DB
   - IS Step 8 will detect missing target
   - Fall back to legacy generation with corpus
   - Works as before

2. **New sessions (post-migration)**: Will have target structure from discovery
   - IS Step 8 will load from DB
   - Skip generation, proceed immediately

3. **Transition sessions**: Discovery completed before migration, upload after
   - Upload page will detect missing target
   - Generate it on-the-fly before IS starts
   - Seamless user experience

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Target generated but IS fails to load | Add retry logic + fallback to legacy generation |
| Timing issue (target not ready before IS Step 5) | Upload page waits for target completion before allowing submit |
| F3iche template missing doctypes user needs | Add LLM enhancement layer reading discovery chat |
| Breaking existing workflows | Comprehensive fallback to legacy path |

## Testing Plan

1. **New session flow**:
   - Complete discovery → click recommendation → land on upload page
   - Verify target structure generated in background
   - Check Supabase `is_target_structures` table
   - Check R2 `_target/target_structure.json`

2. **Old session compatibility**:
   - Start IS workflow for session without target structure
   - Verify Step 8 generates it as before

3. **Race condition test**:
   - Upload files immediately after discovery
   - Verify system waits for target generation

## Success Metrics

- [ ] Target structure generated immediately after discovery
- [ ] No corpus dependencies in target generation
- [ ] IS Step 8 reduced from ~10s to ~0.5s (just loading)
- [ ] Upload page shows "Based on [F3iche], you need these 7 files..."
- [ ] Backward compatibility: old sessions still work
- [ ] No increase in error rate

## Rollout Plan

1. Deploy with feature flag `POST_DISCOVERY_TARGET_ENABLED=0`
2. Test on staging with flag=1
3. Monitor for 24h
4. Enable for 10% of users
5. Gradually increase to 100%
6. Remove legacy code after 2 weeks

---

## Implementation Order

1. ✅ Create `build_post_discovery.py` (new corpus-independent logic)
2. ✅ Refactor `build_target_structure` (remove corpus deps)
3. ✅ Add backend API endpoint
4. ✅ Update IS workflow Step 8 (add load-first logic)
5. ✅ Add frontend trigger on upload page
6. ✅ Test backward compatibility
7. ✅ Update Data Readiness error handling
