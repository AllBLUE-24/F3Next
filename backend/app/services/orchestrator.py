from temporalio.client import Client
from sqlalchemy import update
from shared.database.db import AsyncSessionLocal
from shared.models.core import Project, ProjectStatus # Ensure ProjectStatus is imported

# Configuration
TEMPORAL_HOST = "localhost:7233"

async def trigger_post_config_actions(project_id: str, container_id: str, final_config: dict):
    """
    The Bridge:
    1. Updates DB Status -> DEPLOYMENT_IN_PROGRESS
    2. Triggers 'ConfigApplyWorkflow' & 'TemplateGenWorkflow' in parallel.
    """
    print(f"🥁 ORCHESTRATOR: Launching Deployment for {container_id}...")

    # --- 1. UPDATE DB STATUS ---
    async with AsyncSessionLocal() as session:
        async with session.begin():
            stmt = (
                update(Project)
                .where(Project.id == project_id)
                .values(status=ProjectStatus.DEPLOYMENT_IN_PROGRESS)
            )
            await session.execute(stmt)
            print(f"   ✅ DB Status updated to: {ProjectStatus.DEPLOYMENT_IN_PROGRESS}")

    # --- 2. START TEMPORAL WORKFLOWS ---
    client = await Client.connect(TEMPORAL_HOST)

    # Agent A: Apply Config (The Doer)
    apply_handle = await client.start_workflow(
        "ConfigApplyWorkflow",
        args=[container_id, final_config],
        id=f"apply-{container_id}",
        task_queue="erpnext-apply-queue"
    )
    print(f"   🚀 Started Apply Agent (RunID: {apply_handle.result_run_id})")

    # Agent B: Template Generator (The Creator)
    template_handle = await client.start_workflow(
        "TemplateGenWorkflow",
        args=[project_id, final_config],
        id=f"template-{project_id}",
        task_queue="erpnext-template-queue"
    )
    print(f"   🚀 Started Template Agent (RunID: {template_handle.result_run_id})")

    return {
        "status": "launched",
        "apply_run_id": apply_handle.result_run_id,
        "template_run_id": template_handle.result_run_id
    }