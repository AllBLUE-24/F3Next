from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.db import get_db
from app.models.core import Client, Project

router = APIRouter(prefix="/auth", tags=["Auth"])

class AuthSyncPayload(BaseModel):
    firebase_uid: str
    email: str

@router.post("/sync")
async def sync_user(payload: AuthSyncPayload, db: AsyncSession = Depends(get_db)):
    # Simple check: If user exists, return project_id. If not, create.
    res_c = await db.execute(select(Client).where(Client.id == payload.firebase_uid))
    if not res_c.scalar_one_or_none():
        db.add(Client(id=payload.firebase_uid, email=payload.email))
        # Create default project
        db.add(Project(client_id=payload.firebase_uid, company_name="My Factory"))
        await db.commit()
    
    # Fetch Project ID
    res_p = await db.execute(select(Project).where(Project.client_id == payload.firebase_uid))
    proj = res_p.scalar_one()
    return {"project_id": str(proj.id)}