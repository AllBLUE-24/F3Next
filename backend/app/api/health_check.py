from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.db import get_db
from app.models.core import Client, Project, ProjectStatus
from app.models.hooks import Hook
from pydantic import BaseModel
from typing import Dict, Any, Optional
from uuid import UUID

# Import Agent
from agents.health_check.agent import run_health_check_agent 

router = APIRouter(prefix="/health_check", tags=["Health Check"])

# Schemas
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
    failure_reason: Optional[str] = None # Maps to silver_bullet
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

    # 4. RUN AGENT
    print(f"🚀 Triggering Agent for Project {project.id}")
    agent_result = await run_health_check_agent(payload.answers)

    final_report = ""
    annual_bleed = "Calculating..."

    if isinstance(agent_result, dict):
        final_report = agent_result.get("final_report", "Report generation failed.")
        analysis = agent_result.get("analysis_results", {})
        if isinstance(analysis, dict):
            annual_bleed = analysis.get("total_annual_bleed", "Unknown")
    else:
        final_report = str(agent_result)

    # Save bleed to Project
    project.annual_bleed = str(annual_bleed)
    await db.commit()

    return {
        "status": "success",
        "project_id": str(project.id),
        "report": final_report,
        "annual_bleed": str(annual_bleed),
        "user_meta": {
            "name": client.full_name,
            "company": client.company_name,
            "role": client.role
        }
    }

@router.post("/capture-interest")
async def capture_interest(
    payload: InterestSubmission,
    db: AsyncSession = Depends(get_db),
):
    # 1. Find Project
    try:
        p_uuid = UUID(payload.project_id)
    except ValueError:
         raise HTTPException(status_code=400, detail="Invalid Project ID")

    proj_res = await db.execute(select(Project).where(Project.id == p_uuid))
    project = proj_res.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # 2. Find Client (Using the ID from the project)
    # The info belongs to the Client, so we must fetch them
    client_res = await db.execute(select(Client).where(Client.id == project.client_id))
    client = client_res.scalar_one_or_none()

    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    # 3. Update Status (On Project)
    if payload.status == "interested":
         project.status = ProjectStatus.INTERESTED
    elif payload.status == "listed":
         project.status = ProjectStatus.LISTED

    # 4. Update Info (On Client) - 🔴 CORRECTED MAPPING
    if payload.phone: client.phone_no = payload.phone
    if payload.whatsapp: client.whatsapp_no = payload.whatsapp
    if payload.failure_reason: client.silver_bullet = payload.failure_reason
    if payload.comment: client.comment = payload.comment

    await db.commit()

    return {"status": "updated", "current_status": project.status.value}