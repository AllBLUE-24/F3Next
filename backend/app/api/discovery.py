from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.services.discovery_launcher import start_or_signal_discovery
from sqlalchemy.ext.asyncio import AsyncSession
from shared.database.db import get_shared_db
from shared.models.core import Project
from sqlalchemy import select
from shared.models.hooks import Hook
from uuid import UUID

router = APIRouter(prefix="/discovery", tags=["Discovery"])

class DiscoveryRequest(BaseModel):
    project_id: UUID
    message: str
    step: int = 1

@router.post("/chat")
async def chat_discovery(request: DiscoveryRequest, db: AsyncSession = Depends(get_shared_db)):
    """
    Receives user message and signals the Temporal Discovery Workflow.
    """
    # 1. Validate Project
    res = await db.execute(select(Project).where(Project.id == request.project_id))
    project = res.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        # 2. Trigger Temporal Signal
        workflow_id = await start_or_signal_discovery(
            project_id=str(project.id),
            user_message=request.message
        )

        return {
            "status": "sent",
            "workflow_id": workflow_id,
            "message": "Message received by Discovery Agent."
        }
    except Exception as e:
        print(f"❌ Discovery Launch Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{project_id}")
async def get_discovery_status(project_id: UUID, db: AsyncSession = Depends(get_shared_db)):
    """
    Polls the latest state of the Discovery Chat for the Frontend.
    """
    try:
        # Fetch the latest bot response and extracted data
        query = select(Hook).where(Hook.project_id == project_id)
        result = await db.execute(query)
        hook = result.scalar_one_or_none()

        if not hook:
            raise HTTPException(status_code=404, detail="Discovery session not found")

        discovery_metadata = hook.discovery_metadata or {}
        return {
            "bot_response": hook.last_bot_response,  # The latest question
            "extracted_tags": hook.extracted_tags,   # For the 'Detected Attributes' UI
            "step": hook.discovery_step,             # Current step (1-5)
            "status": hook.discovery_status,         # START, RETRY, or COMPLETE
            "is_complete": hook.discovery_status == "COMPLETE",
            "f3iche": discovery_metadata.get("f3iche"),
            "industry": discovery_metadata.get("industry"),
            "price_plan": discovery_metadata.get("price_plan"),
            "recommended_erp": discovery_metadata.get("recommended_erp"),
            "fit_score": discovery_metadata.get("fit_score"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{project_id}/recommendation")
async def get_recommendation_status(project_id: UUID, db: AsyncSession = Depends(get_shared_db)):
    """
    Dedicated endpoint for the Recommendation Page to poll final ERP results.
    """
    try:
        query = select(Hook).where(Hook.project_id == project_id)
        result = await db.execute(query)
        hook = result.scalar_one_or_none()

        if not hook:
            raise HTTPException(status_code=404, detail="Project context not found")

        # If the metadata is null or empty, Temporal is still processing
        if not hook.discovery_metadata:
            return {"status": "processing"}

        # Once Temporal writes the JSON to this column, we return it!
        return {
            "status": "ready",
            "data": hook.discovery_metadata
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))