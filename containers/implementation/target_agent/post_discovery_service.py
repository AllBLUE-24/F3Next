"""
Post-Discovery Target Structure Generation Service

Called when user clicks "Proceed to Implementation" on recommendation page.
Generates target structure and MVP boundary at PROJECT level.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional
from uuid import UUID

import boto3
from botocore.config import Config
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.project_target import ProjectTargetStructure, ProjectMVPBoundary
from shared.models.hooks import Hook
from containers.implementation.target_agent.build_post_discovery import (
    build_post_discovery_target,
)


def _get_s3_client():
    """Get R2/S3 client for storing target structure and MVP boundary."""
    return boto3.client(
        "s3",
        endpoint_url=os.getenv("R2_ENDPOINT"),
        aws_access_key_id=os.getenv("R2_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("R2_SECRET_ACCESS_KEY"),
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )


async def generate_project_target_structure(
    db: AsyncSession,
    project_id: UUID,
    company_slug: str,
) -> Dict[str, Any]:
    """
    Generate and store project-level target structure and MVP boundary.
    
    This is called AFTER discovery completion, when user clicks "Proceed to Implementation".
    
    Args:
        db: Database session
        project_id: Project UUID
        company_slug: Company slug for R2 path
    
    Returns:
        Dict with:
            - target_structure_id: UUID
            - mvp_boundary_id: UUID
            - seed_doctypes: List[str]
            - required_doctypes: List[str]
            - r2_target_path: str
            - r2_mvp_path: str
    """
    # 1. Load discovery metadata from Hook
    stmt = select(Hook).where(Hook.project_id == project_id)
    result = await db.execute(stmt)
    hook = result.scalar_one_or_none()
    
    if not hook or not hook.discovery_metadata:
        raise ValueError(f"Discovery not complete for project {project_id}")
    
    metadata = hook.discovery_metadata
    f3iche = metadata.get("f3iche", "trading")
    mvp_focus = metadata.get("mvp_focus", {})
    
    print(f"🎯 Generating project target structure | project={project_id} f3iche={f3iche}")
    
    # 2. Generate target structure using build_post_discovery_target
    target_result = await build_post_discovery_target(
        f3iche=f3iche,
        mvp_focus=mvp_focus,
        discovery_chat=hook.chat_history if hasattr(hook, 'chat_history') else None,
        enhance_with_llm=False,  # Future enhancement
    )
    
    # 3. Store in R2
    s3 = _get_s3_client()
    bucket = "clean-data"
    
    # Target structure path
    target_key = f"{company_slug}/project_{project_id}/_discovery/target_structure.json"
    target_json = json.dumps(target_result, indent=2)
    s3.put_object(Bucket=bucket, Key=target_key, Body=target_json.encode("utf-8"))
    
    # MVP boundary path
    mvp_boundary_data = target_result.get("mvp_boundary", {})
    mvp_key = f"{company_slug}/project_{project_id}/_discovery/mvp_boundary.json"
    mvp_json = json.dumps(mvp_boundary_data, indent=2)
    s3.put_object(Bucket=bucket, Key=mvp_key, Body=mvp_json.encode("utf-8"))
    
    print(f"  ✅ Stored in R2: {target_key}")
    print(f"  ✅ Stored in R2: {mvp_key}")
    
    # 4. Store ProjectTargetStructure in DB
    target_structure = ProjectTargetStructure(
        project_id=project_id,
        f3iche=f3iche,
        discovery_bottleneck=mvp_focus.get("primary_bottleneck"),
        llm_enhanced=target_result.get("llm_enhanced", False),
        llm_reasoning=target_result.get("llm_reasoning"),
        total_doctypes=len(target_result.get("required_doctypes", [])),
        total_seed_doctypes=len(target_result.get("seed_doctypes", [])),
        total_setup_steps=len(target_result.get("setup_steps", [])),
        r2_target_path=target_key,
        r2_mvp_path=mvp_key,
        seed_doctypes=target_result.get("seed_doctypes", []),
        required_doctypes=target_result.get("required_doctypes", []),
        setup_steps=target_result.get("setup_steps", []),
        import_phases=target_result.get("import_phases", {}),
        validation_rules=target_result.get("validation_rules", {}),
        mvp_focus=mvp_focus,
        deferred_doctypes=target_result.get("deferred_doctypes", []),
        corpus_independent=True,
        graph_driven=True,
    )
    
    # Check if already exists and delete old one
    existing_stmt = select(ProjectTargetStructure).where(
        ProjectTargetStructure.project_id == project_id
    )
    existing = (await db.execute(existing_stmt)).scalar_one_or_none()
    if existing:
        await db.delete(existing)
    
    db.add(target_structure)
    await db.flush()
    
    print(f"  ✅ ProjectTargetStructure saved | id={target_structure.id}")
    
    # 5. Store ProjectMVPBoundary in DB
    mvp_boundary = ProjectMVPBoundary(
        project_id=project_id,
        f3iche=f3iche,
        primary_bottleneck=mvp_focus.get("primary_bottleneck"),
        functional_requirements=mvp_focus.get("functional_requirements", []),
        seed_doctypes=target_result.get("seed_doctypes", []),
        deferred_doctypes=target_result.get("deferred_doctypes", []),
        mode=mvp_boundary_data.get("mode", "f3iche_template"),
        llm_enhanced=mvp_boundary_data.get("llm_enhanced", False),
        llm_reasoning=mvp_boundary_data.get("llm_reasoning"),
        r2_path=mvp_key,
    )
    
    # Check if already exists and delete old one
    existing_mvp_stmt = select(ProjectMVPBoundary).where(
        ProjectMVPBoundary.project_id == project_id
    )
    existing_mvp = (await db.execute(existing_mvp_stmt)).scalar_one_or_none()
    if existing_mvp:
        await db.delete(existing_mvp)
    
    db.add(mvp_boundary)
    await db.commit()
    
    print(f"  ✅ ProjectMVPBoundary saved | id={mvp_boundary.id}")
    print(f"  ✅ Complete! Seeds: {len(target_result.get('seed_doctypes', []))} → Total: {len(target_result.get('required_doctypes', []))}")
    
    return {
        "target_structure_id": str(target_structure.id),
        "mvp_boundary_id": str(mvp_boundary.id),
        "seed_doctypes": target_result.get("seed_doctypes", []),
        "required_doctypes": target_result.get("required_doctypes", []),
        "total_doctypes": len(target_result.get("required_doctypes", [])),
        "total_seeds": len(target_result.get("seed_doctypes", [])),
        "r2_target_path": target_key,
        "r2_mvp_path": mvp_key,
        "f3iche": f3iche,
    }
