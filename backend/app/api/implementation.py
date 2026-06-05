"""
Implementation API routes — thin layer over ImplementationLauncher.
Every endpoint either starts a workflow, sends a signal, or queries state.
No business logic lives here.
"""
from __future__ import annotations
import os
import boto3
from botocore.config import Config
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from pydantic import BaseModel
from shared.database.db import AsyncSessionLocal
from sqlalchemy.future import select
from shared.models.core import Project
from shared.models.is_models import ISSession, ISFile
from app.services.is_launcher import ImplementationLauncher

router = APIRouter(prefix="/implementation", tags=["Implementation"])


# ── Dep helper ────────────────────────────────────────────────────────────────

async def get_launcher() -> ImplementationLauncher:
    return ImplementationLauncher()


class PresignedUrlRequest(BaseModel):
    project_id: UUID
    file_names: List[str]

@router.post("/presigned-urls", summary="Generate direct R2 upload URLs")
async def generate_presigned_urls(req: PresignedUrlRequest):
    # Retrieve company slug from DB to organize R2 paths
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(Project).where(Project.id == req.project_id))
        proj = res.scalar_one_or_none()
        company_slug = proj.company_slug if proj else "unknown"

    # Connect to Cloudflare R2
    s3_client = boto3.client(
        "s3",
        endpoint_url=os.getenv("R2_ENDPOINT"),
        aws_access_key_id=os.getenv("R2_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("R2_SECRET_ACCESS_KEY"),
        config=Config(signature_version="s3v4"),
        region_name="auto"
    )

    bucket_name = "quarantine"
    urls = []

    for file_name in req.file_names:
        object_key = f"{company_slug}/{str(req.project_id)}/{file_name}"
        
        presigned_url = s3_client.generate_presigned_url(
            'put_object',
            Params={'Bucket': bucket_name, 'Key': object_key},
            ExpiresIn=3600
        )
        
        urls.append({
            "file_name": file_name,
            "upload_url": presigned_url,
            "object_path": object_key
        })

    return {"urls": urls}

    
# ══════════════════════════════════════════════════════════════════════════════
# Workflow lifecycle
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/start/{project_id}", summary="Start or resume the implementation workflow")
async def start_workflow(
    project_id: UUID,
    background_tasks: BackgroundTasks,
    launcher: ImplementationLauncher = Depends(get_launcher),
):
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(Project).where(Project.id == project_id))
        proj = res.scalar_one_or_none()
        company_slug = proj.company_slug if proj else "unknown"

    impl_result = await launcher.start(project_id)
    return impl_result


# ══════════════════════════════════════════════════════════════════════════════
# Signals  (one endpoint per human action in the UI)
# ══════════════════════════════════════════════════════════════════════════════

class FilesUploadedRequest(BaseModel):
    project_id: UUID
    uploaded_files: List[Dict[str, Any]]         # [{file_name, object_path}]
    company_slug: Optional[str] = None
    user_note: Optional[str] = None


@router.post("/signal/files-uploaded", summary="Notify workflow that files have been uploaded")
async def signal_files_uploaded(
    req: FilesUploadedRequest,
    launcher: ImplementationLauncher = Depends(get_launcher),
):
    import asyncio
    is_session = None
    
    # Poll for the ISSession. Temporal might take a second to reach Step 0
    # and write to the database after the workflow starts.
    for _ in range(10):
        async with AsyncSessionLocal() as session:
            res = await session.execute(
                select(ISSession)
                .where(ISSession.project_id == req.project_id)
                .order_by(ISSession.created_at.desc())
                .limit(1)
            )
            is_session = res.scalars().first()
        
        if is_session:
            break
        await asyncio.sleep(0.5)
        
    if not is_session:
        # This usually means the workflow hasn't reached Step 0 yet (persist_session)
        raise HTTPException(
            status_code=404, 
            detail="Implementation session not found. Please ensure the workflow has started."
        )

    # 2. Insert record for each file into is_files table
    async with AsyncSessionLocal() as session:
        for f in req.uploaded_files:
            new_file = ISFile(
                session_id=is_session.id,
                original_filename=f["file_name"],
                r2_object_key=f["object_path"],
                bucket_location="quarantine-data",
                virus_scan_status="pending"
            )
            session.add(new_file)
        
        # Commit to ensure rows exist before triggering Temporal activity
        await session.commit()

    # 3. Trigger the files_uploaded signal to the Temporal workflow
    await launcher.signal_files_uploaded(
        req.project_id,
        req.uploaded_files,
        req.company_slug,
        req.user_note,
    )
    return {"ok": True, "signal": "files_uploaded"}


class F3icheConfirmedRequest(BaseModel):
    project_id: UUID
    accepted: bool = True
    correction_text: Optional[str] = None
    # Legacy override (optional when accepted=true — synthesis proposal is used)
    f3iche_user: Optional[str] = None
    industry: Optional[str] = None
    industry_sub: Optional[str] = None
    company_name: Optional[str] = None
    company_size: Optional[str] = None


@router.get("/f3iche/confirmation/{project_id}", summary="F3iche confirmation proposal for UI gate")
async def get_f3iche_confirmation(
    project_id: UUID,
    launcher: ImplementationLauncher = Depends(get_launcher),
):
    try:
        confirmation = await launcher.get_f3iche_confirmation(project_id)
        return {"ok": True, "confirmation": confirmation}
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/signal/f3iche-confirmed", summary="User confirms or corrects proposed business type")
async def signal_f3iche_confirmed(
    req: F3icheConfirmedRequest,
    launcher: ImplementationLauncher = Depends(get_launcher),
):
    try:
        result = await launcher.confirm_f3iche(
            req.project_id,
            accepted=req.accepted,
            correction_text=req.correction_text,
            f3iche_user=req.f3iche_user,
            industry=req.industry,
            industry_sub=req.industry_sub,
            company_name=req.company_name,
            company_size=req.company_size,
        )
        return {"ok": True, "signal": "f3iche_confirmed", **result}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


class MappingConfirmedRequest(BaseModel):
    project_id: UUID
    user_feedback: Optional[str] = None
    approved: bool = False


@router.post("/signal/mapping-confirmed", summary="User confirmed or provided feedback on automated mappings")
async def signal_mapping_confirmed(
    req: MappingConfirmedRequest,
    launcher: ImplementationLauncher = Depends(get_launcher),
):
    await launcher.signal_mapping_confirmed(
        req.project_id, req.user_feedback, req.approved
    )
    return {"ok": True, "signal": "mapping_confirmed"}



class ValidationSubmittedRequest(BaseModel):
    project_id: UUID
    responses: Dict[str, Any]
    profile_edits: Optional[Dict[str, Any]] = None
    note: Optional[str] = None


@router.post("/signal/validation-submitted", summary="User has resolved all validation items")
async def signal_validation_submitted(
    req: ValidationSubmittedRequest,
    launcher: ImplementationLauncher = Depends(get_launcher),
):
    await launcher.signal_validation_submitted(
        req.project_id, req.responses, req.profile_edits, req.note
    )
    return {"ok": True, "signal": "validation_submitted"}


class SandboxApprovedRequest(BaseModel):
    project_id: UUID
    erpnext_base_url: str = ""      # Optional — auto-resolved from Project.deployment_details
    erpnext_api_key: str = ""       # Optional — auto-resolved from Project.deployment_details
    dry_run: bool = False


@router.post("/signal/sandbox-approved", summary="Sandbox verified — proceed with live import")
async def signal_sandbox_approved(
    req: SandboxApprovedRequest,
    launcher: ImplementationLauncher = Depends(get_launcher),
):
    await launcher.signal_sandbox_approved(
        req.project_id, req.erpnext_base_url, req.erpnext_api_key, req.dry_run
    )
    return {"ok": True, "signal": "sandbox_approved"}


# ══════════════════════════════════════════════════════════════════════════════
# Queries  (read-only state polling)
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/state/{project_id}", summary="Full workflow state in one call")
async def get_full_state(
    project_id: UUID,
    launcher: ImplementationLauncher = Depends(get_launcher),
):
    try:
        return await launcher.get_full_state(project_id)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/stage/{project_id}", summary="Current pipeline stage")
async def get_stage(
    project_id: UUID,
    launcher: ImplementationLauncher = Depends(get_launcher),
):
    return {"stage": await launcher.get_stage(project_id)}


@router.get("/tasks/{project_id}", summary="Granular analysis task list (for /analyze page)")
async def get_analysis_tasks(
    project_id: UUID,
    launcher: ImplementationLauncher = Depends(get_launcher),
):
    return {"tasks": await launcher.get_analysis_tasks(project_id)}


@router.get("/profile/{project_id}", summary="Latest company profile snapshot")
async def get_profile(
    project_id: UUID,
    launcher: ImplementationLauncher = Depends(get_launcher),
):
    return {"profile": await launcher.get_profile(project_id)}


@router.get("/validation/{project_id}", summary="Validation report")
async def get_validation_report(
    project_id: UUID,
    launcher: ImplementationLauncher = Depends(get_launcher),
):
    report = await launcher.get_validation_report(project_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Validation not yet run")
    return {"validation_report": report}


@router.get("/corpus-assignments/{project_id}", summary="Per-file doctype classification")
async def get_corpus_assignments(
    project_id: UUID,
    launcher: ImplementationLauncher = Depends(get_launcher),
):
    assignments = await launcher.get_corpus_assignments(project_id)
    return {"corpus_assignments": assignments}


@router.get("/data-readiness/{project_id}", summary="Data readiness assessment")
async def get_data_readiness(
    project_id: UUID,
    launcher: ImplementationLauncher = Depends(get_launcher),
):
    report = await launcher.get_data_readiness(project_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Data readiness not yet assessed")
    return {"data_readiness": report}


@router.get("/import-plan/{project_id}", summary="3-phase import plan")
async def get_import_plan(
    project_id: UUID,
    launcher: ImplementationLauncher = Depends(get_launcher),
):
    plan = await launcher.get_import_plan(project_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Import plan not yet built")
    return {"import_plan": plan}


@router.get("/import-results/{project_id}", summary="Live import phase results")
async def get_import_results(
    project_id: UUID,
    launcher: ImplementationLauncher = Depends(get_launcher),
):
    return {"import_results": await launcher.get_import_results(project_id)}


@router.post("/re-finalize-plan/{project_id}", summary="Re-run finalize_import_plan for stale plans")
async def re_finalize_import_plan(
    project_id: UUID,
    launcher: ImplementationLauncher = Depends(get_launcher),
):
    try:
        return await launcher.re_finalize_import_plan(project_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/validate-preview/{project_id}", summary="Full data preview for validation — all mapped payloads")
async def get_validate_preview(
    project_id: UUID,
    launcher: ImplementationLauncher = Depends(get_launcher),
):
    preview = await launcher.get_validate_preview(project_id)
    if "error" in preview:
        raise HTTPException(status_code=404, detail=preview["error"])
    return preview


# ══════════════════════════════════════════════════════════════════════════════
# Supervisor prompts (exception-driven conversation)
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/supervisor-prompts/{project_id}", summary="Open Supervisor prompts for this project")
async def get_supervisor_prompts(
    project_id: UUID,
    launcher: ImplementationLauncher = Depends(get_launcher),
):
    return {"prompts": await launcher.get_supervisor_prompts(project_id)}


class SupervisorRespondRequest(BaseModel):
    project_id: UUID
    prompt_id: str
    chosen_action_id: str
    extra_data: Optional[Dict[str, Any]] = None


@router.post("/supervisor-prompts/respond", summary="Answer a Supervisor prompt and signal workflow")
async def respond_supervisor_prompt(
    req: SupervisorRespondRequest,
    launcher: ImplementationLauncher = Depends(get_launcher),
):
    try:
        await launcher.answer_supervisor_prompt(
            req.project_id,
            req.prompt_id,
            req.chosen_action_id,
            extra_data=req.extra_data,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"ok": True}


# ══════════════════════════════════════════════════════════════════════════════
# Chat bar (free-text assistant)
# ══════════════════════════════════════════════════════════════════════════════


class ChatSendRequest(BaseModel):
    message: str
    step: str = "analyze"  # upload | analyze | validate | import


@router.get("/chat/{project_id}", summary="Chat history for implementation session")
async def get_chat_history(
    project_id: UUID,
    step: Optional[str] = None,
    limit: int = 100,
    launcher: ImplementationLauncher = Depends(get_launcher),
):
    messages = await launcher.get_chat_messages(project_id, step=step, limit=limit)
    return {"messages": messages}


@router.post("/chat/{project_id}", summary="Send a message to the implementation assistant")
async def send_chat_message(
    project_id: UUID,
    req: ChatSendRequest,
    launcher: ImplementationLauncher = Depends(get_launcher),
):
    try:
        response = await launcher.send_chat_message(
            project_id,
            req.message,
            step=req.step,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger = __import__("logging").getLogger(__name__)
        logger.exception("Chat dispatch failed")
        raise HTTPException(status_code=500, detail="Chat dispatch failed") from exc
    return {"message": response}
