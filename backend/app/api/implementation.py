"""Implementation system API — F3iche, signals, profile, target, mapping, validation, import."""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.db import get_db
from shared.models.core import Project
from shared.models.hooks import Hook
from app.services.implementation.company_profile import CompanyProfileService
from app.services.implementation.signals_inference import SignalsInferenceService
from app.services.implementation.f3iche_verification import F3icheVerificationService
from app.services.implementation.target_structure import TargetStructureService
from app.services.implementation.mapping_engine import MappingEngine
from app.services.implementation.validation_engine import ValidationEngine
from app.services.implementation.import_engine import ImportEngine

router = APIRouter(prefix="/implementation", tags=["Implementation"])


# --- Request/Response Models ---

class SignalsInferRequest(BaseModel):
    project_id: UUID
    uploaded_files: List[Dict[str, Any]]  # [{file_name, object_path}]
    file_contents: Optional[Dict[str, str]] = None  # filename -> text content


class F3icheVerifyRequest(BaseModel):
    project_id: UUID
    f3iche_user: str
    f3iche_signals: str
    confidence: float = 0.0


class TargetStructureRequest(BaseModel):
    project_id: UUID
    f3iche: str
    industry: Optional[str] = None


class MapFileRequest(BaseModel):
    content: str
    filename: str
    doctype_hint: Optional[str] = None


class ValidateRequest(BaseModel):
    project_id: UUID
    mapped_data: Dict[str, Any]
    target_structure: Dict[str, Any]


class ImportPlanRequest(BaseModel):
    project_id: UUID
    target_structure: Dict[str, Any]
    mapped_data: Dict[str, Any]
    validation_report: Dict[str, Any]


# --- Endpoints ---

@router.get("/profile/{project_id}")
async def get_company_profile(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get latest company profile for project."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(404, "Project not found")
    profile = project.implementation_profile or {}
    return {"profile": profile, "project_id": str(project_id)}


@router.post("/signals/infer")
async def infer_f3iche_from_files(request: SignalsInferRequest):
    """Infer F3iche from uploaded files using signals_registry."""
    svc = SignalsInferenceService()
    f3iche_id, confidence, signals = svc.infer_f3iche(
        request.uploaded_files,
        request.file_contents,
    )
    return {
        "f3iche": f3iche_id,
        "confidence": round(confidence, 2),
        "collected_signals": signals,
    }


@router.post("/f3iche/verify")
async def verify_f3iche_match(request: F3icheVerifyRequest):
    """Verify user F3iche vs signals-inferred F3iche."""
    svc = F3icheVerificationService()
    is_match, status, msg = svc.verify(
        request.f3iche_user,
        request.f3iche_signals,
        request.confidence,
    )
    return {
        "is_match": is_match,
        "status": status,
        "clarification_message": msg,
    }


@router.post("/target-structure")
async def build_target_structure(request: TargetStructureRequest):
    """Build target structure (action workflow) for implementation."""
    svc = TargetStructureService()
    target = svc.build_target_structure(
        request.f3iche,
        request.industry,
    )
    return {"target_structure": target}


@router.post("/map-file")
async def map_file_to_erpnext(request: MapFileRequest):
    """Map uploaded file content to ERPNext doctype and fields."""
    engine = MappingEngine()
    result = engine.map_file_to_erpnext(
        request.content,
        request.filename,
        request.doctype_hint,
    )
    return result


@router.post("/validate")
async def validate_mapped_data(request: ValidateRequest):
    """Validate mapped data before import."""
    engine = ValidationEngine()
    report = engine.validate_mapped_data(
        request.mapped_data,
        request.target_structure,
    )
    return {"validation_report": report}


@router.post("/import/plan")
async def build_import_plan(request: ImportPlanRequest):
    """Build 3-phase import plan."""
    engine = ImportEngine()
    plan = engine.build_import_plan(
        request.target_structure,
        request.mapped_data,
        request.validation_report,
    )
    return {"import_plan": plan}


class ProfileUpdateRequest(BaseModel):
    project_id: UUID
    f3iche: str
    industry: str
    industry_sub: Optional[str] = None
    company_size: Optional[str] = None
    company_name: Optional[str] = None
    f3iche_user: Optional[str] = None
    f3iche_signals: Optional[str] = None
    f3iche_match_status: str = "matched"
    uploaded_files: Optional[List[Dict]] = None
    collected_signals: Optional[List[str]] = None
    target_structure: Optional[Dict] = None
    field_mappings: Optional[Dict] = None
    validation_report: Optional[Dict] = None
    import_phase: Optional[str] = None
    action: str = "update"


@router.post("/profile/update")
async def update_company_profile(
    request: ProfileUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update company profile (versioned)."""
    result = await db.execute(select(Project).where(Project.id == request.project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(404, "Project not found")

    current = project.implementation_profile or {}
    version = current.get("version", 0) + 1

    profile = CompanyProfileService.build_profile(
        project_id=str(request.project_id),
        version=version,
        f3iche=request.f3iche,
        industry=request.industry,
        industry_sub=request.industry_sub,
        company_size=request.company_size,
        company_name=request.company_name,
        f3iche_user=request.f3iche_user,
        f3iche_signals=request.f3iche_signals,
        f3iche_match_status=request.f3iche_match_status,
        uploaded_files=request.uploaded_files or current.get("uploaded_files"),
        collected_signals=request.collected_signals or current.get("collected_signals"),
        target_structure=request.target_structure or current.get("target_structure"),
        field_mappings=request.field_mappings or current.get("field_mappings"),
        validation_report=request.validation_report or current.get("validation_report"),
        import_phase=request.import_phase or current.get("import_phase"),
        action=request.action,
    )

    project.implementation_profile = profile
    await db.commit()
    await db.refresh(project)

    return {"profile": profile, "version": version}


@router.get("/f3iche/list")
async def list_f3iches():
    """List available F3iches."""
    import json
    from pathlib import Path
    KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "implementation" / "knowledge"
    f3iches = []
    for p in KNOWLEDGE_DIR.glob("f3iche_*.json"):
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
            meta = data.get("_meta", {})
            f3iches.append({
                "id": meta.get("id", p.stem.replace("f3iche_", "")),
                "name": meta.get("name", ""),
                "description": meta.get("description", ""),
            })
    return {"f3iches": f3iches}
