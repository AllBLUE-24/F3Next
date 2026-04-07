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

        async with AsyncSessionLocal() as session:
            stmt = (
                update(Project)
                .where(Project.id == payload.project_id)
                .values(status=ProjectStatus.DEPLOYMENT_IN_PROGRESS)
            )
            await session.execute(stmt)
            await session.commit()

        return {
            "status": "triggered",
            "workflow_id": workflow_id,
            "message": "Infrastructure provisioning started."
        }
    except Exception as e:
        print(f"❌ Error triggering workflow: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/deployment/{project_id}")
async def get_deployment_state(project_id: str):
    """
    Polled by the frontend to render the top spinning container UI bar.
    Tracks live Postgres status as the Infra Agent manipulates the cloud endpoints.
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        if not project:
            raise HTTPException(404, "Project not found")

        # Map Postgres string models to Frontend UI expectation blocks
        status_map = {
            ProjectStatus.DEPLOYMENT_IN_PROGRESS: 'deploying',
            ProjectStatus.DEPLOYMENT_COMPLETED: 'ready',
        }
        status = status_map.get(project.status, 'pending')

        return {
            "status": status,
            "progress": 50 if status == 'deploying' else (100 if status == 'ready' else 0),
            "instanceUrl": (project.deployment_details.get("url") or project.deployment_details.get("site_url")) if project.deployment_details else None,
            "userId": project.deployment_details.get("user_id", "Administrator") if project.deployment_details else "Administrator",
            "adminPassword": project.deployment_details.get("admin_password") if project.deployment_details else None,
            "api_key": project.deployment_details.get("api_key") if project.deployment_details else None,
            "api_secret": project.deployment_details.get("api_secret") if project.deployment_details else None,
            "container_id": project.deployment_details.get("container_id") if project.deployment_details else None,
            "region": "ap-south-1",
            "erpSoftware": "ERPNext",
            "startedAt": str(project.created_at),
            "readyAt": str(project.updated_at) if status == 'ready' else None,
        }

@router.get("/deployment/slug/{company_slug}")
async def get_deployment_state_by_slug(company_slug: str):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Project).where(Project.company_slug == company_slug))
        project = result.scalar_one_or_none()
        if not project:
            raise HTTPException(404, "Project not found")

        status_map = {
            ProjectStatus.DEPLOYMENT_IN_PROGRESS: 'deploying',
            ProjectStatus.DEPLOYMENT_COMPLETED: 'ready',
        }
        status = status_map.get(project.status, 'pending')

        return {
            "status": status,
            "progress": 50 if status == 'deploying' else (100 if status == 'ready' else 0),
            "instanceUrl": (project.deployment_details.get("url") or project.deployment_details.get("site_url")) if project.deployment_details else None,
            "userId": project.deployment_details.get("user_id", "Administrator") if project.deployment_details else "Administrator",
            "adminPassword": project.deployment_details.get("admin_password") if project.deployment_details else None,
            "api_key": project.deployment_details.get("api_key") if project.deployment_details else None,
            "api_secret": project.deployment_details.get("api_secret") if project.deployment_details else None,
            "container_id": project.deployment_details.get("container_id") if project.deployment_details else None,
            "region": "ap-south-1",
            "erpSoftware": "ERPNext",
            "startedAt": str(project.created_at),
            "readyAt": str(project.updated_at) if status == 'ready' else None,
        }