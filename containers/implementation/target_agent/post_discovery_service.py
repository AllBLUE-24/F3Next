"""
Post-Discovery Target Structure Generation Service

Called when discovery completes (and again on module confirmation).
Generates target structure and MVP boundary at PROJECT level.
"""
from __future__ import annotations

import logging
from typing import Any, Dict
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.project_target import ProjectTargetStructure, ProjectMVPBoundary
from shared.models.hooks import Hook
from shared.r2_client import r2_write_json_verified
from containers.implementation.target_agent.build_post_discovery import (
    build_post_discovery_target,
)
from containers.discovery.f3iche_resolver import resolve_discovery_f3iche_niche
from containers.discovery.chat_service import transcript_text, normalize_messages

logger = logging.getLogger(__name__)


async def generate_project_target_structure(
    db: AsyncSession,
    project_id: UUID,
    company_slug: str,
    *,
    user_confirmed_seeds: list[str] | None = None,
    user_added_doctypes: list[str] | None = None,
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
    
    if not hook:
        raise ValueError(f"No discovery session for project {project_id}")
    if not hook.discovery_metadata:
        raise ValueError(
            f"Discovery metadata missing for project {project_id}. "
            "Complete discovery chat before generating target structure."
        )
    
    metadata = hook.discovery_metadata
    broad_f3iche = metadata.get("f3iche", "trading")
    mvp_focus = metadata.get("mvp_focus", {})
    industry = metadata.get("industry", "")

    messages = normalize_messages(hook.chat_history)
    chat_transcript = transcript_text(messages)

    f3iche = metadata.get("f3iche_niche") or resolve_discovery_f3iche_niche(
        discovery_f3iche=broad_f3iche,
        industry=industry,
        chat_transcript=chat_transcript,
    )

    seed_override: list[str] | None = None
    if user_confirmed_seeds:
        seed_override = list(dict.fromkeys(user_confirmed_seeds))
        if user_added_doctypes:
            seed_override = list(dict.fromkeys(seed_override + list(user_added_doctypes)))

    logger.debug(
        "Generating project target structure | project=%s f3iche=%s",
        project_id,
        f3iche,
    )

    target_result = await build_post_discovery_target(
        f3iche=f3iche,
        mvp_focus=mvp_focus,
        discovery_chat=messages,
        coverage=hook.discovery_coverage,
        chat_transcript=chat_transcript,
        enhance_with_llm=False,
        seed_doctypes_override=seed_override,
    )
    
    # 3. Store in R2 (clean-data bucket — same as IS pipeline)
    bucket = "clean-data"
    target_key = f"{company_slug}/project_{project_id}/_discovery/target_structure.json"
    mvp_boundary_data = target_result.get("mvp_boundary") or {}
    if not mvp_boundary_data.get("seed_doctypes"):
        raise RuntimeError(
            "MVP boundary missing seed_doctypes — cannot persist empty boundary"
        )
    mvp_key = f"{company_slug}/project_{project_id}/_discovery/mvp_boundary.json"

    ok_target = await r2_write_json_verified(
        target_key, target_result, bucket=bucket, min_bytes=10
    )
    ok_mvp = await r2_write_json_verified(
        mvp_key, mvp_boundary_data, bucket=bucket, min_bytes=10
    )
    if not ok_target or not ok_mvp:
        raise RuntimeError(
            f"R2 upload failed for discovery artifacts | target_ok={ok_target} mvp_ok={ok_mvp}"
        )
    logger.debug("R2 stored discovery artifacts | target=%s mvp=%s", target_key, mvp_key)
    
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
        target_structure_json=target_result,
        mvp_boundary_json=mvp_boundary_data,
        corpus_independent=True,
        graph_driven=True,
    )

    # Replace existing row (flush delete before insert — unique on project_id)
    existing_stmt = select(ProjectTargetStructure).where(
        ProjectTargetStructure.project_id == project_id
    )
    existing = (await db.execute(existing_stmt)).scalar_one_or_none()
    if existing:
        await db.delete(existing)
        await db.flush()

    db.add(target_structure)
    await db.flush()

    logger.debug("ProjectTargetStructure saved | id=%s", target_structure.id)
    
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
        llm_reasoning=mvp_boundary_data.get("llm_reasoning") or mvp_boundary_data.get("scoping_reasoning"),
        r2_path=mvp_key,
    )
    
    existing_mvp_stmt = select(ProjectMVPBoundary).where(
        ProjectMVPBoundary.project_id == project_id
    )
    existing_mvp = (await db.execute(existing_mvp_stmt)).scalar_one_or_none()
    if existing_mvp:
        await db.delete(existing_mvp)
        await db.flush()

    db.add(mvp_boundary)
    await db.flush()

    logger.debug(
        "Discovery target complete | seeds=%s total=%s",
        len(target_result.get("seed_doctypes", [])),
        len(target_result.get("required_doctypes", [])),
    )
    
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
        "target_structure": target_result,
    }
