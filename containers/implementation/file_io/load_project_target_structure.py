"""
Load project-level target structure and MVP boundary.

This replaces the session-level target loading for corpus-independent implementations.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict
from uuid import UUID

import boto3
from botocore.config import Config
from temporalio import activity
from sqlalchemy import select

from shared.database.db import AsyncSessionLocal
from shared.models.project_target import ProjectTargetStructure, ProjectMVPBoundary
from shared.models.is_models import ISSession, ISTargetStructure


def _get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=os.getenv("R2_ENDPOINT"),
        aws_access_key_id=os.getenv("R2_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("R2_SECRET_ACCESS_KEY"),
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )


@dataclass
class LoadProjectTargetInput:
    session_id: str


async def _materialize_session_target(
    db: Any,
    *,
    session_id: UUID,
    project_target: ProjectTargetStructure,
    required_doctypes: list[str],
    setup_steps: list[dict[str, Any]],
    import_phases: dict[str, Any],
) -> None:
    """Mirror the canonical project target into the active IS session."""
    stmt = (
        select(ISTargetStructure)
        .where(ISTargetStructure.session_id == session_id)
        .order_by(ISTargetStructure.created_at.desc())
        .limit(1)
    )
    session_target = (await db.execute(stmt)).scalar_one_or_none()
    values = {
        "f3iche": project_target.f3iche,
        "llm_enhanced": bool(project_target.llm_enhanced),
        "llm_reasoning": project_target.llm_reasoning,
        "total_doctypes": len(required_doctypes),
        "total_setup_steps": len(setup_steps),
        "r2_path": project_target.r2_target_path,
        "required_doctypes": required_doctypes,
        "setup_steps": setup_steps,
        "import_phases": import_phases,
        "validation_rules": project_target.validation_rules or {},
    }
    if session_target:
        for key, value in values.items():
            setattr(session_target, key, value)
    else:
        db.add(ISTargetStructure(session_id=session_id, **values))
    await db.commit()


@activity.defn(name="load_project_target_structure")
async def load_project_target_structure(inp: LoadProjectTargetInput) -> Dict[str, Any]:
    """
    Load project-level target structure (corpus-independent).
    
    Returns:
        Dict with:
        - required_doctypes: list
        - seed_doctypes: list
        - setup_steps: list
        - import_phases: dict
        - mvp_boundary: dict
        - exists: bool (True if found, False otherwise)
        - source: "project_level" or "not_found"
    """
    activity.logger.info("▶ load_project_target_structure | session_id=%s", inp.session_id)
    
    try:
        async with AsyncSessionLocal() as db:
            # 1. Get project_id from session
            session_stmt = select(ISSession).where(ISSession.id == UUID(inp.session_id))
            session = (await db.execute(session_stmt)).scalar_one_or_none()
            
            if not session:
                activity.logger.warning("  ⚠️ Session not found: %s", inp.session_id)
                return {"exists": False, "source": "not_found"}
            
            project_id = session.project_id
            
            # 2. Load ProjectTargetStructure
            target_stmt = (
                select(ProjectTargetStructure)
                .where(ProjectTargetStructure.project_id == project_id)
                .order_by(ProjectTargetStructure.created_at.desc())
                .limit(1)
            )
            target = (await db.execute(target_stmt)).scalar_one_or_none()
            
            if not target:
                activity.logger.info("  ⚠️ No project-level target structure found for project %s", project_id)
                return {"exists": False, "source": "not_found"}
            
            # 3. Load MVP Boundary
            mvp_stmt = select(ProjectMVPBoundary).where(
                ProjectMVPBoundary.project_id == project_id
            )
            mvp = (await db.execute(mvp_stmt)).scalar_one_or_none()
            
            # 4. Parse JSON fields
            required = target.required_doctypes
            if isinstance(required, str):
                required = json.loads(required)
            
            seeds = target.seed_doctypes
            if isinstance(seeds, str):
                seeds = json.loads(seeds)
            
            steps = target.setup_steps
            if isinstance(steps, str):
                steps = json.loads(steps)
            
            phases = target.import_phases
            if isinstance(phases, str):
                phases = json.loads(phases)
            
            # 5. Build MVP boundary — prefer consolidated column on target row
            mvp_boundary: dict = {}
            if target.mvp_boundary_json and isinstance(target.mvp_boundary_json, dict):
                mvp_boundary = dict(target.mvp_boundary_json)
            elif mvp:
                mvp_boundary = {
                    "mode": mvp.mode,
                    "f3iche": mvp.f3iche,
                    "seed_doctypes": mvp.seed_doctypes if isinstance(mvp.seed_doctypes, list) else json.loads(mvp.seed_doctypes or "[]"),
                    "deferred_doctypes": mvp.deferred_doctypes if isinstance(mvp.deferred_doctypes, list) else json.loads(mvp.deferred_doctypes or "[]"),
                    "mvp_focus": {
                        "primary_bottleneck": mvp.primary_bottleneck,
                        "functional_requirements": mvp.functional_requirements if isinstance(mvp.functional_requirements, list) else json.loads(mvp.functional_requirements or "[]"),
                    },
                    "llm_enhanced": mvp.llm_enhanced,
                    "llm_reasoning": mvp.llm_reasoning,
                }
            
            result = {
                "required_doctypes": required or [],
                "seed_doctypes": seeds or [],
                "setup_steps": steps or [],
                "import_phases": phases or {},
                "validation_rules": target.validation_rules or {},
                "mvp_boundary": mvp_boundary,
                "deferred_doctypes": mvp_boundary.get("deferred_doctypes") or (target.deferred_doctypes or []),
                "exists": True,
                "source": "project_level",
                "corpus_independent": True,
                "r2_target_path": target.r2_target_path,
                "r2_mvp_path": target.r2_mvp_path,
                "f3iche": target.f3iche,
                "total_doctypes": target.total_doctypes,
                "total_seeds": target.total_seed_doctypes,
            }

            # Downstream readiness, mapping, validation, and import activities are
            # session-scoped and query is_target_structures. Loading the project
            # target without this snapshot made those nodes behave as if no target
            # existed even though the workflow-local variable was correct.
            await _materialize_session_target(
                db,
                session_id=UUID(inp.session_id),
                project_target=target,
                required_doctypes=result["required_doctypes"],
                setup_steps=result["setup_steps"],
                import_phases=result["import_phases"],
            )
            
            activity.logger.info(
                "  ✅ Project-level target loaded | seeds=%d total=%d source=project_level",
                len(result["seed_doctypes"]),
                len(result["required_doctypes"])
            )
            
            return result
    
    except Exception as e:
        activity.logger.error("  ❌ Failed to load project target structure: %s", e)
        return {"exists": False, "source": "error", "error": str(e)}
