from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from shared.database.db import get_shared_db
from shared.models.core import Client, Project, ProjectStatus

router = APIRouter(prefix="/onboarding", tags=["Onboarding"])

class OnboardingRequest(BaseModel):
    user_id: str
    email: Optional[str] = ""   # Optional — some OAuth providers don't expose email
    full_name: str
    user_slug: str
    role: str
    company_name: str
    company_slug: str

@router.get("/check-slug")
async def check_slug(
    type: str = Query(..., regex="^(company|user)$"), 
    slug: str = Query(...), 
    db: AsyncSession = Depends(get_shared_db)
):
    """
    Checks if a slug is already taken. Returns true if available.
    """
    if type == "company":
        query = select(Project).where(Project.company_slug == slug)
    else:
        query = select(Client).where(Client.user_slug == slug)
        
    result = await db.execute(query)
    exists = result.scalar_one_or_none()
    
    return {"available": not exists}

@router.post("/complete")
async def complete_onboarding(
    data: OnboardingRequest, 
    db: AsyncSession = Depends(get_shared_db)
):
    """
    Saves user details and creates the company project.
    """
    # 1. Update Client (User)
    query = select(Client).where(Client.id == data.user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if not user:
        # Create if doesn't exist (if Trigger missed)
        user = Client(id=data.user_id, email=data.email)
        db.add(user)
    else:
        # Update email if changed or missing
        user.email = data.email
    
    user.full_name = data.full_name
    user.user_slug = data.user_slug
    user.role = data.role
    user.company_name = data.company_name
    
    # 2. Create/Update Project
    # Check if user already has a project
    p_query = select(Project).where(Project.client_id == data.user_id)
    p_result = await db.execute(p_query)
    project = p_result.scalar_one_or_none()
    
    if not project:
        project = Project(
            client_id=user.id,
            company_name=data.company_name,
            company_slug=data.company_slug,
            status=ProjectStatus.CREATED
        )
        db.add(project)
    else:
        project.company_name = data.company_name
        project.company_slug = data.company_slug

    try:
        await db.commit()
        return {
            "status": "success", 
            "redirect_url": f"/{data.company_slug}/{data.user_slug}/home"
        }
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Slug might already be taken. {str(e)}")