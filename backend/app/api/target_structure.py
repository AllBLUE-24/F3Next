"""
Target Structure Generation API

Handles post-discovery target structure generation (before file upload).
"""
from uuid import UUID
import json
import asyncio

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from temporalio.client import Client as TemporalClient

from shared.database.db import get_shared_db, AsyncSessionLocal
from shared.models.hooks import Hook
from shared.models.is_models import ISTargetStructure, ISSession
from shared.models.core import Project

router = APIRouter(prefix="/target", tags=["Target Structure"])


class GenerateTargetRequest(BaseModel):
    project_id: UUID


class TargetStatusResponse(BaseModel):
    status: str  # "generating", "ready", "error"
    target_id: UUID | None = None
    total_doctypes: int | None = None
    seed_doctypes: list[str] | None = None
    error: str | None = None


@router.post("/generate", summary="Generate target structure post-discovery")
async def generate_target_structure(
    request: GenerateTargetRequest,
    db: AsyncSession = Depends(get_shared_db),
):
    """
    Generate target structure after discovery completion, before file upload.
    
    This runs async and doesn't block. The frontend can poll /target/status to check completion.
    """
    project_id = request.project_id
    
    # 1. Verify project exists
    project_result = await db.execute(select(Project).where(Project.id == project_id))
    project = project_result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # 2. Check if target structure already exists
    existing = await db.execute(
        select(ISTargetStructure)
        .where(ISTargetStructure.session_id == project_id)
        .order_by(ISTargetStructure.created_at.desc())
        .limit(1)
    )
    if existing.scalar_one_or_none():
        return {
            "status": "already_exists",
            "message": "Target structure already generated for this project"
        }
    
    # 3. Load discovery metadata from hooks table
    hook_result = await db.execute(select(Hook).where(Hook.project_id == project_id))
    hook = hook_result.scalar_one_or_none()
    
    if not hook or not hook.discovery_metadata:
        raise HTTPException(
            status_code=400,
            detail="Discovery not complete. Please complete discovery first."
        )
    
    discovery_metadata = hook.discovery_metadata
    f3iche = discovery_metadata.get("f3iche", "trading")
    mvp_focus = discovery_metadata.get("mvp_focus")
    
    # 4. Get discovery chat history for LLM enhancement (optional)
    discovery_chat = hook.chat_history or []
    
    # 5. Trigger async target structure generation
    # Using asyncio.create_task so it runs in background
    asyncio.create_task(
        _generate_target_async(
            project_id=project_id,
            company_slug=project.slug,
            f3iche=f3iche,
            mvp_focus=mvp_focus,
            discovery_chat=discovery_chat,
        )
    )
    
    return {
        "status": "generating",
        "message": "Target structure generation started",
        "f3iche": f3iche,
    }


@router.get("/status/{project_id}", summary="Check target structure generation status")
async def get_target_status(
    project_id: UUID,
    db: AsyncSession = Depends(get_shared_db),
) -> TargetStatusResponse:
    """
    Poll target structure generation status.
    """
    result = await db.execute(
        select(ISTargetStructure)
        .where(ISTargetStructure.session_id == project_id)
        .order_by(ISTargetStructure.created_at.desc())
        .limit(1)
    )
    target = result.scalar_one_or_none()
    
    if not target:
        return TargetStatusResponse(status="not_found")
    
    # Parse JSON fields
    seed_doctypes = target.required_doctypes
    if isinstance(seed_doctypes, str):
        seed_doctypes = json.loads(seed_doctypes)
    
    return TargetStatusResponse(
        status="ready",
        target_id=target.id,
        total_doctypes=target.total_doctypes,
        seed_doctypes=seed_doctypes[:10] if seed_doctypes else [],  # Preview only
    )


async def _generate_target_async(
    *,
    project_id: UUID,
    company_slug: str,
    f3iche: str,
    mvp_focus: dict | None,
    discovery_chat: list[dict],
):
    """
    Background task to generate target structure.
    
    This runs independently and saves to DB when complete.
    """
    import uuid
    from containers.discovery.target.build_target import build_post_discovery_target
    from containers.implementation.target_agent.mvp_boundary import build_mvp_boundary
    from containers.implementation.file_io.persist_audit import log_audit
    import boto3
    import os
    
    print(f"🎯 [ASYNC] Starting target generation for project {project_id}")
    
    try:
        # Generate target structure
        result = await build_post_discovery_target(
            f3iche=f3iche,
            mvp_focus=mvp_focus,
            discovery_chat=discovery_chat,
            enhance_with_llm=False,  # TODO: Enable when LLM enhancement is implemented
        )
        
        seed_doctypes = result.get("seed_doctypes", [])
        all_required = result.get("required_doctypes", [])
        setup_steps = result.get("setup_steps", [])
        import_phases = result.get("import_phases", {})
        mvp_boundary = result.get("mvp_boundary", {})
        
        # Save to R2
        s3 = boto3.client(
            "s3",
            endpoint_url=os.getenv("R2_ENDPOINT"),
            aws_access_key_id=os.getenv("R2_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("R2_SECRET_ACCESS_KEY"),
            region_name="auto",
        )
        
        # Target structure
        target_key = f"{company_slug}/{project_id}/_target/target_structure.json"
        s3.put_object(
            Bucket="clean-data",
            Key=target_key,
            Body=json.dumps(result, indent=2, default=str).encode("utf-8"),
            ContentType="application/json",
        )
        print(f"  ✅ R2: clean-data/{target_key}")
        
        # MVP boundary
        mvp_key = f"{company_slug}/{project_id}/_target/mvp_boundary.json"
        s3.put_object(
            Bucket="clean-data",
            Key=mvp_key,
            Body=json.dumps(mvp_boundary, indent=2, default=str).encode("utf-8"),
            ContentType="application/json",
        )
        print(f"  ✅ R2: clean-data/{mvp_key}")
        
        # Save to Supabase
        target_id = uuid.uuid4()
        async with AsyncSessionLocal() as session:
            session.add(ISTargetStructure(
                id=target_id,
                session_id=project_id,
                f3iche=f3iche,
                llm_enhanced=result.get("mvp_boundary", {}).get("llm_enhanced", False),
                llm_reasoning=result.get("mvp_boundary", {}).get("llm_reasoning", ""),
                total_doctypes=len(all_required),
                total_setup_steps=len(setup_steps),
                required_doctypes=json.dumps(all_required),
                setup_steps=json.dumps(setup_steps),
                import_phases=json.dumps(import_phases),
                r2_path=target_key,
            ))
            await session.commit()
        
        print(f"  ✅ Supabase: is_target_structures (id={target_id})")
        
        # Audit log
        async with AsyncSessionLocal() as session:
            await log_audit(
                session_id=str(project_id),
                action="target_generated_post_discovery",
                actor="system",
                entity_type="target_structure",
                entity_id=str(target_id),
                details={
                    "f3iche": f3iche,
                    "seed_doctypes": len(seed_doctypes),
                    "total_doctypes": len(all_required),
                    "setup_steps": len(setup_steps),
                    "corpus_independent": True,
                    "generated_at": "post_discovery",
                },
            )
        
        print(f"✅ [ASYNC] Target generation complete for project {project_id}")
        
    except Exception as e:
        print(f"❌ [ASYNC] Target generation failed: {e!r}")
        # TODO: Store error state in DB for frontend to poll
        async with AsyncSessionLocal() as session:
            await log_audit(
                session_id=str(project_id),
                action="target_generation_failed",
                actor="system",
                entity_type="target_structure",
                entity_id="",
                details={"error": str(e), "f3iche": f3iche},
            )
