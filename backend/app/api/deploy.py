from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from shared.database.db import AsyncSessionLocal
from shared.models.core import Project, ProjectStatus
from sqlalchemy.future import select
from sqlalchemy import update

from app.services.deploy_launcher import launch_downstream_workflows, trigger_infra_provisioning

router = APIRouter(tags=["Deployment"])

class DeployPayload(BaseModel):
    project_id: str
    container_id: str

class InfraRequest(BaseModel):
    project_id: str
    company_slug: str
    tier: str = "standard"

@router.post("/deploy/start")
async def start_deployment(payload: DeployPayload, background_tasks: BackgroundTasks):
    """
    Called by Frontend when Config is COMPLETED.
    1. Updates DB status to DEPLOYMENT_IN_PROGRESS.
    2. Kicks off the next workflows via deploy_launcher.
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Project).where(Project.id == payload.project_id))
        project = result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(404, "Project not found")
        
        if project.status == ProjectStatus.DEPLOYMENT_IN_PROGRESS:
             return {"status": "already_deploying"}

        config_data = project.processed_config
        if not config_data:
            raise HTTPException(400, "No processed config found. Complete the Config Agent first.")

        stmt = (
            update(Project)
            .where(Project.id == payload.project_id)
            .values(status=ProjectStatus.DEPLOYMENT_IN_PROGRESS)
        )
        await session.execute(stmt)
        await session.commit()

    # Launch Agents (Background Task safely offloads to Launcher)
    background_tasks.add_task(launch_downstream_workflows, payload.project_id, payload.container_id, config_data)

    return {"status": "deployment_launched"}

@router.post("/deploy/infra")
async def trigger_infra_deployment(payload: InfraRequest):
    """
    Provisions cloud infrastructure (receives JSON from Frontend -> Starts Temporal Workflow).
    """
    try:
        workflow_id = await trigger_infra_provisioning(
            project_id=payload.project_id,
            company_slug=payload.company_slug,
            tier=payload.tier
        )
        return {
            "status": "triggered",
            "workflow_id": workflow_id,
            "message": "Infrastructure provisioning started."
        }
    except Exception as e:
        print(f"❌ Error triggering workflow: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))