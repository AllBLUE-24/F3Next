from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.discovery_chat import (
    confirm_discovery_modules,
    finalize_discovery,
    load_session,
    load_workflow_preview,
    send_chat_message,
    submit_clarification_answers,
)
from shared.database.db import get_shared_db
from shared.models.core import Project
from shared.models.hooks import Hook
from shared.models.project_target import ProjectMVPBoundary, ProjectTargetStructure
from containers.discovery.phases import DiscoveryPhase, get_phase, is_upload_ready
from containers.discovery.target.persist import generate_project_target_structure

router = APIRouter(prefix="/discovery", tags=["Discovery"])


class DiscoveryRequest(BaseModel):
    project_id: UUID
    message: str
    step: int = 1  # legacy — ignored


class CompleteRequest(BaseModel):
    project_id: UUID


class ConfirmModulesRequest(BaseModel):
    project_id: UUID
    confirmed_doctypes: list[str]
    added_doctypes: list[str] = []
    removed_doctypes: list[str] = []
    notes: str = ""


class ClarificationRequest(BaseModel):
    project_id: UUID
    answers: dict[str, str | list[str]]


@router.get("/session/{project_id}")
async def get_discovery_session(project_id: UUID, db: AsyncSession = Depends(get_shared_db)):
    """Load chat history and session state (ChatGPT-style — no polling needed)."""
    res = await db.execute(select(Project).where(Project.id == project_id))
    if not res.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        return await load_session(db, project_id)
    except Exception as e:
        print(f"❌ Discovery session error: {e!r}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat")
async def chat_discovery(request: DiscoveryRequest, db: AsyncSession = Depends(get_shared_db)):
    """
    Synchronous discovery chat — send a message, get Adi's reply immediately.
    Stores full history in hooks.chat_history (JSONB).
    """
    res = await db.execute(select(Project).where(Project.id == request.project_id))
    if not res.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found")

    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    try:
        result = await send_chat_message(db, request.project_id, request.message)
        return result
    except Exception as e:
        print(f"❌ Discovery chat error: {e!r}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/complete")
async def complete_discovery(request: CompleteRequest, db: AsyncSession = Depends(get_shared_db)):
    """
    End discovery — extract signals from full transcript + generate ERP recommendation.
    Writes discovery_metadata for IS handoff.
    """
    res = await db.execute(select(Project).where(Project.id == request.project_id))
    if not res.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        return await finalize_discovery(db, request.project_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"❌ Discovery complete error: {e!r}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/blueprint-status")
async def get_blueprint_status(project_id: UUID, db: AsyncSession = Depends(get_shared_db)):
    """
    Check stored MVP boundary + target structure for a project (Discovery Assistant Step 1).
    Logs appear on the FastAPI backend process, not the IS Temporal worker.
    """
    hook_result = await db.execute(select(Hook).where(Hook.project_id == project_id))
    hook = hook_result.scalar_one_or_none()

    target_result = await db.execute(
        select(ProjectTargetStructure).where(ProjectTargetStructure.project_id == project_id)
    )
    target = target_result.scalar_one_or_none()

    mvp_result = await db.execute(
        select(ProjectMVPBoundary).where(ProjectMVPBoundary.project_id == project_id)
    )
    mvp = mvp_result.scalar_one_or_none()

    metadata = (hook.discovery_metadata if hook else None) or {}
    phase = metadata.get("phase", "initial_chat")

    return {
        "discovery_status": hook.discovery_status if hook else None,
        "phase": phase,
        "target_structure": {
            "stored": target is not None,
            "id": str(target.id) if target else None,
            "f3iche": target.f3iche if target else None,
            "seed_doctypes": target.seed_doctypes if target else None,
            "deferred_doctypes": target.deferred_doctypes if target else None,
            "total_doctypes": target.total_doctypes if target else None,
            "r2_path": target.r2_target_path if target else None,
            "json_column_stored": bool(target and target.target_structure_json),
        },
        "mvp_boundary": {
            "stored": bool(mvp or (target and target.mvp_boundary_json)),
            "id": str(mvp.id) if mvp else None,
            "seed_doctypes": (
                (target.mvp_boundary_json or {}).get("seed_doctypes")
                if target and target.mvp_boundary_json
                else (mvp.seed_doctypes if mvp else None)
            ),
            "deferred_doctypes": (
                (target.mvp_boundary_json or {}).get("deferred_doctypes")
                if target and target.mvp_boundary_json
                else (mvp.deferred_doctypes if mvp else None)
            ),
            "primary_bottleneck": (
                ((target.mvp_boundary_json or {}).get("mvp_focus") or {}).get("primary_bottleneck")
                if target and target.mvp_boundary_json
                else (mvp.primary_bottleneck if mvp else None)
            ),
            "scoping_mode": (
                (target.mvp_boundary_json or {}).get("mode")
                if target and target.mvp_boundary_json
                else (mvp.mode if mvp else None)
            ),
            "r2_path": target.r2_mvp_path if target else (mvp.r2_path if mvp else None),
            "json_column_stored": bool(target and target.mvp_boundary_json),
        },
        "hooks_metadata_has_target": bool(metadata.get("target_structure")),
    }


@router.post("/clarification")
async def submit_clarification(request: ClarificationRequest, db: AsyncSession = Depends(get_shared_db)):
    """Submit answers to pre-plan clarifying questions, then generate MVP plan."""
    res = await db.execute(select(Project).where(Project.id == request.project_id))
    if not res.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found")

    if not request.answers:
        raise HTTPException(status_code=400, detail="At least one answer is required")

    try:
        return await submit_clarification_answers(
            db, request.project_id, dict(request.answers)
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"❌ Discovery clarification error: {e!r}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/workflow-preview")
async def get_workflow_preview(project_id: UUID, db: AsyncSession = Depends(get_shared_db)):
    """Structured workflow + upload checklist for Discovery Assistant Step 1."""
    res = await db.execute(select(Project).where(Project.id == project_id))
    if not res.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        return await load_workflow_preview(db, project_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"❌ Workflow preview error: {e!r}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/confirm-modules")
async def confirm_modules(request: ConfirmModulesRequest, db: AsyncSession = Depends(get_shared_db)):
    """User confirms MVP modules and files — finalizes target before upload."""
    res = await db.execute(select(Project).where(Project.id == request.project_id))
    if not res.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found")

    if not request.confirmed_doctypes:
        raise HTTPException(status_code=400, detail="Select at least one module to continue")

    try:
        return await confirm_discovery_modules(
            db,
            request.project_id,
            confirmed_doctypes=request.confirmed_doctypes,
            added_doctypes=request.added_doctypes,
            removed_doctypes=request.removed_doctypes,
            notes=request.notes,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"❌ Confirm modules error: {e!r}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{project_id}")
async def get_discovery_status(project_id: UUID, db: AsyncSession = Depends(get_shared_db)):
    """Backward-compatible status endpoint — delegates to session loader."""
    try:
        session = await load_session(db, project_id)
        return {
            "bot_response": (
                session["messages"][-1]["content"]
                if session.get("messages")
                else ""
            ),
            "messages": session.get("messages", []),
            "extracted_tags": [],
            "step": 1,
            "turn_count": session.get("user_turns", 0),
            "status": session.get("status"),
            "is_complete": session.get("is_complete", False),
            "coverage": session.get("coverage") or {
                "industry": {"status": None, "value": None},
                "strategy": {"status": None, "value": None},
                "scale": {"status": None, "value": None},
                "legacy_system": {"status": None, "value": None},
                "pain_point": {"status": None, "value": None},
            },
            "ready_for_recommendation": session.get("ready_for_recommendation", False),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/recommendation")
async def get_recommendation_status(project_id: UUID, db: AsyncSession = Depends(get_shared_db)):
    """Poll final ERP recommendation (ready immediately after POST /complete)."""
    try:
        query = select(Hook).where(Hook.project_id == project_id)
        result = await db.execute(query)
        hook = result.scalar_one_or_none()

        if not hook:
            raise HTTPException(status_code=404, detail="Project context not found")

        if not hook.discovery_metadata:
            return {"status": "processing"}

        metadata = hook.discovery_metadata or {}
        phase = get_phase(metadata)
        finalized = is_upload_ready(metadata)

        if phase == DiscoveryPhase.CLARIFICATION:
            return {
                "status": "incomplete",
                "phase": phase.value,
                "awaiting_confirmation": False,
                "redirect_to_discovery": True,
                "clarifying_questions": metadata.get("clarifying_questions") or [],
                "data": metadata,
            }

        has_workflow = bool(metadata.get("workflow_explanation"))
        has_target = bool((metadata.get("target_structure") or {}).get("seed_doctypes"))

        return {
            "status": "ready",
            "phase": phase.value,
            "awaiting_confirmation": not finalized and phase in (
                DiscoveryPhase.WORKFLOW_DISPLAY,
                DiscoveryPhase.MODULE_CONFIRMATION,
            ),
            "plan_incomplete": not finalized and (not has_workflow or not has_target),
            "data": metadata,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{project_id}/proceed-to-implementation")
async def proceed_to_implementation(project_id: UUID, db: AsyncSession = Depends(get_shared_db)):
    """
    Generate project-level target structure and MVP boundary after discovery completion.
    Called when user clicks "Proceed to Implementation" on recommendation page.
    
    This generates corpus-independent artifacts that will be reused across all IS runs.
    """
    try:
        # Verify project exists
        project_query = select(Project).where(Project.id == project_id)
        result = await db.execute(project_query)
        project = result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        if not project.company_slug:
            raise HTTPException(status_code=400, detail="Project missing company_slug")
        
        # Verify discovery is complete
        hook_query = select(Hook).where(Hook.project_id == project_id)
        hook_result = await db.execute(hook_query)
        hook = hook_result.scalar_one_or_none()
        
        if not hook or not hook.discovery_metadata:
            raise HTTPException(
                status_code=400,
                detail="Discovery not complete. Please complete discovery first."
            )

        phase = (hook.discovery_metadata or {}).get("phase")
        if phase != "finalized":
            raise HTTPException(
                status_code=400,
                detail="Confirm your implementation workflow and modules before proceeding to upload."
            )
        
        # Regenerate if needed (idempotent — target already stored at confirm)
        result_data = await generate_project_target_structure(
            db=db,
            project_id=project_id,
            company_slug=project.company_slug,
        )
        await db.commit()

        return {
            "status": "success",
            "message": "Target structure and MVP boundary generated successfully",
            "data": result_data,
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"❌ Proceed to implementation error: {e!r}")
        raise HTTPException(status_code=500, detail=str(e))
