import os
from temporalio.client import Client
from dotenv import load_dotenv

load_dotenv()
TEMPORAL_HOST = os.getenv("TEMPORAL_HOST")

async def launch_downstream_workflows(project_id: str, container_id: str, config_data: dict):
    client = await Client.connect(TEMPORAL_HOST)
    print(f"[DeployLauncher] Launching downstream agents for project {project_id}")

    try:
        await client.start_workflow(
            "ConfigApplyWorkflow",
            args=[container_id, config_data],
            id=f"apply-{container_id}",
            task_queue="erpnext-apply-queue"
        )
        print("   ✅ Apply Agent Started")
    except Exception as e:
        print(f"   ⚠️ Apply Agent start failed (might be running): {e}")

    try:
        await client.start_workflow(
            "TemplateGenWorkflow",
            args=[project_id, config_data],
            id=f"template-{project_id}",
            task_queue="erpnext-template-queue"
        )
        print("   ✅ Template Agent Started")
    except Exception as e:
        print(f"   ⚠️ Template Agent start failed: {e}")


async def trigger_infra_provisioning(project_id: str, company_slug: str, tier: str):
    client = await Client.connect(TEMPORAL_HOST)
    workflow_input = {
        "project_id": project_id,
        "company_slug": company_slug,
        "tier": tier
    }
    
    handle = await client.start_workflow(
        "ERPNextProvisioningWorkflow",
        workflow_input,
        id=f"provision-{project_id}", 
        task_queue="erpnext-provisioning-queue",
    )
    return handle.id
