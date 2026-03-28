from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from temporalio.client import Client
from shared.database.db import AsyncSessionLocal
from shared.models.core import Project, ProjectStatus
from sqlalchemy.future import select
from sqlalchemy import update
import os
from dotenv import load_dotenv
load_dotenv()


router = APIRouter()
TEMPORAL_HOST = os.getenv("TEMPORAL_HOST")

class DeployPayload(BaseModel):
    project_id: str
    container_id: str

async def launch_downstream_workflows(project_id: str, container_id: str, config_data: dict):
    """
    Helper function to start the parallel agents.
    """
    client = await Client.connect(TEMPORAL_HOST)
    print(f"[Deploy] Launching downstream agents for project {project_id}")

    # 1. Start Apply Agent (Updates ERPNext Settings)
    try:
        await client.start_workflow(
            "ConfigApplyWorkflow",
            args=[container_id, config_data],
            id=f"apply-{container_id}",
            task_queue="erpnext-apply-queue"
        )
        print(f"   ✅ Apply Agent Started")
    except Exception as e:
        print(f"   ⚠️ Apply Agent start failed (might be running): {e}")

    # 2. Start Template Agent (Generates CSVs)
    try:
        await client.start_workflow(
            "TemplateGenWorkflow",
            args=[project_id, config_data],
            id=f"template-{project_id}",
            task_queue="erpnext-template-queue"
        )
        print(f"   ✅ Template Agent Started")
    except Exception as e:
        print(f"   ⚠️ Template Agent start failed: {e}")

@router.post("/deploy/start")
async def start_deployment(payload: DeployPayload, background_tasks: BackgroundTasks):
    """
    Called by Frontend when Config is COMPLETED.
    1. Updates DB status to DEPLOYMENT_IN_PROGRESS.
    2. Kicks off the next workflows.
    """
    # 1. Fetch Project & Config
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Project).where(Project.id == payload.project_id))
        project = result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(404, "Project not found")
        
        # Check if we already moved past this stage to avoid double-triggers
        if project.status == ProjectStatus.DEPLOYMENT_IN_PROGRESS:
             return {"status": "already_deploying"}

        config_data = project.processed_config
        if not config_data:
            raise HTTPException(400, "No processed config found. Complete the Config Agent first.")

        # 2. Update Status in DB
        stmt = (
            update(Project)
            .where(Project.id == payload.project_id)
            .values(status=ProjectStatus.DEPLOYMENT_IN_PROGRESS)
        )
        await session.execute(stmt)
        await session.commit()

    # 3. Launch Agents (Background Task so API returns fast)
    background_tasks.add_task(launch_downstream_workflows, payload.project_id, payload.container_id, config_data)

    return {"status": "deployment_launched"}