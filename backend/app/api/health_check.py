from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.db import get_db
from shared.models.core import Client, Project, ProjectStatus
from shared.models.hooks import Hook
from pydantic import BaseModel
from typing import Dict, Any, Optional
from uuid import UUID
from app.services.health_check_launcher import start_health_check_flow

router = APIRouter(prefix="/health_check", tags=["Health Check"])

# --- Schemas ---
class AnonymousSubmission(BaseModel):
    firebase_uid: str
    user_email: str
    full_name: str
    role: str
    company_name: str
    answers: Dict[str, Any]

class InterestSubmission(BaseModel):
    project_id: str
    status: str 
    phone: Optional[str] = None
    whatsapp: Optional[str] = None
    failure_reason: Optional[str] = None 
    comment: Optional[str] = None

@router.post("/submit")
async def submit_health_check(
    payload: AnonymousSubmission,
    db: AsyncSession = Depends(get_db),
):
    # 1. ENSURE CLIENT
    client_res = await db.execute(select(Client).where(Client.id == payload.firebase_uid))
    client = client_res.scalar_one_or_none()
    
    if not client:
        # Note: annual_bleed must be nullable in DB for this to work
        client = Client(
            id=payload.firebase_uid, 
            email=payload.user_email,
            full_name=payload.full_name,
            role=payload.role,
            company_name=payload.company_name,
            status="active"
        )
        db.add(client)
        await db.flush()

    # 2. ENSURE PROJECT
    proj_res = await db.execute(select(Project).where(Project.client_id == payload.firebase_uid))
    project = proj_res.scalar_one_or_none()

    if not project:
        project = Project(
            client_id=payload.firebase_uid, 
            company_name=payload.company_name,
            status=ProjectStatus.CREATED 
        )
        db.add(project)
        await db.flush()

        project_id_str = str(project.id) #

    # 3. HOOKS
    hook_res = await db.execute(select(Hook).where(Hook.project_id == project.id))
    existing_hook = hook_res.scalar_one_or_none()

    if existing_hook:
        existing_hook.answers_health_check = payload.answers
    else:
        new_hook = Hook(
            project_id=project.id,
            answers_health_check=payload.answers
        )
        db.add(new_hook)

    await db.commit()

    # --- 4. RUN TEMPORAL AGENT ---
    project_id_str = str(project.id)
    print(f"[HealthCheck] Triggering workflow for project {project_id_str}")

    try:
        # Crucial: Pass the firebase_uid and answers. 
        # If your launcher needs project_id, pass project_id_str
        workflow_id = await start_health_check_flow(
            uid=payload.firebase_uid, 
            answers=payload.answers,
            project_id=project_id_str
        )

        return {
            "status": "success",
            "project_id": project_id_str,
            "workflow_id": workflow_id,
            "message": "Analysis started in background.",
            "user_meta": {
                "name": client.full_name,
                "company": client.company_name,
                "role": client.role
            }
        }
    except Exception as e:
        # This captures the 'dns error' or 'connection refused' if Temporal is down
        print(f"❌ Temporal Launch Error: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to start workflow: {str(e)}"
        )

@router.post("/capture-interest")
async def capture_interest(
    payload: InterestSubmission,
    db: AsyncSession = Depends(get_db),
):
    try:
        p_uuid = UUID(payload.project_id)
    except ValueError:
         raise HTTPException(status_code=400, detail="Invalid Project ID format")

    proj_res = await db.execute(select(Project).where(Project.id == p_uuid))
    project = proj_res.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    client_res = await db.execute(select(Client).where(Client.id == project.client_id))
    client = client_res.scalar_one_or_none()

    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    # Update Status
    if payload.status == "interested":
         project.status = ProjectStatus.INTERESTED
    elif payload.status == "listed":
         project.status = ProjectStatus.LISTED

    # Update Client Details
    if payload.phone: client.phone_no = payload.phone
    if payload.whatsapp: client.whatsapp_no = payload.whatsapp
    if payload.failure_reason: client.silver_bullet = payload.failure_reason
    if payload.comment: client.comment = payload.comment

    await db.commit()
    return {"status": "updated", "current_status": project.status.value}
    

@router.get("/status/{project_id}")
async def get_report_status(project_id: str, db: AsyncSession = Depends(get_db)):
    # Fetch the hook to check if report_content is populated
    query = select(Hook, Project).join(Project).where(Hook.project_id == project_id)
    result = await db.execute(query)
    hook, project = result.first() or (None, None)   

    if not hook:
        raise HTTPException(status_code=404, detail="Project not found")
        
    return {
        "is_ready": hook.report_content is not None,
        "report_content": hook.report_content,
        "annual_bleed": project.annual_bleed # Pass the real number here
    }


    