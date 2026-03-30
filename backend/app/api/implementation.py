"""
Implementation API routes — thin layer over ImplementationLauncher.
Every endpoint either starts a workflow, sends a signal, or queries state.
No business logic lives here.

Replaces: backend/app/services/implementation/implementation.py (old direct-service router)
"""
from __future__ import annotations
import os
import boto3
from botocore.config import Config
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
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
        object_key = f"{str(req.project_id)}/{file_name}"
        
        # Generate a URL valid for 1 hour (3600 seconds) for a PUT request
        presigned_url = s3_client.generate_presigned_url(
            'put_object',
            Params={'Bucket': bucket_name, 'Key': object_key},
            ExpiresIn=3600
        )
        
        urls.append({
            "file_name": file_name,
            "upload_url": presigned_url,
            "object_path": object_key # This is the address Temporal needs later!
        })

    return {"urls": urls}

    
# ══════════════════════════════════════════════════════════════════════════════
# Workflow lifecycle
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/start/{project_id}", summary="Start or resume the implementation workflow")
async def start_workflow(
    project_id: UUID,
    launcher: ImplementationLauncher = Depends(get_launcher),
):
    return await launcher.start(project_id)


# ══════════════════════════════════════════════════════════════════════════════
# Signals  (one endpoint per human action in the UI)
# ══════════════════════════════════════════════════════════════════════════════

class FilesUploadedRequest(BaseModel):
    project_id: UUID
    uploaded_files: List[Dict[str, Any]]         # [{file_name, object_path}]
    file_contents: Optional[Dict[str, str]] = None  # filename → raw text




@router.post("/signal/files-uploaded", summary="Notify workflow that files have been uploaded")
async def signal_files_uploaded(
    req: FilesUploadedRequest,
    launcher: ImplementationLauncher = Depends(get_launcher),
):
    await launcher.signal_files_uploaded(req.project_id, req.uploaded_files, req.file_contents)
    return {"ok": True, "signal": "files_uploaded"}


class F3icheConfirmedRequest(BaseModel):
    project_id: UUID
    f3iche_user: str
    industry: str
    industry_sub: Optional[str] = None
    company_name: Optional[str] = None
    company_size: Optional[str] = None


@router.post("/signal/f3iche-confirmed", summary="User has confirmed their business type")
async def signal_f3iche_confirmed(
    req: F3icheConfirmedRequest,
    launcher: ImplementationLauncher = Depends(get_launcher),
):
    await launcher.signal_f3iche_confirmed(
        req.project_id, req.f3iche_user, req.industry,
        req.industry_sub, req.company_name, req.company_size,
    )
    return {"ok": True, "signal": "f3iche_confirmed"}


class FilesMappedRequest(BaseModel):
    project_id: UUID
    mapped_data: Dict[str, Any]   # {doctype: {field_mapping, rows, ...}}


@router.post("/signal/files-mapped", summary="Upload mapped file data to the workflow")
async def signal_files_mapped(
    req: FilesMappedRequest,
    launcher: ImplementationLauncher = Depends(get_launcher),
):
    await launcher.signal_files_mapped(req.project_id, req.mapped_data)
    return {"ok": True, "signal": "files_mapped"}


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
    erpnext_base_url: str
    erpnext_api_key: str
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