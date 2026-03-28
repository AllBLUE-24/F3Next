from temporalio.client import Client
import os
from dotenv import load_dotenv
load_dotenv()


async def start_config_workflow(container_id: str, project_id: str, initial_tags: list):
    # CONFIGURATION
    TEMPORAL_HOST = os.getenv("TEMPORAL_HOST")
    
    client = await Client.connect(TEMPORAL_HOST)    
    
    workflow_id = f"config-workflow-{container_id}"
    
    await client.start_workflow(
        "ConfigWorkflow",
        # 🔴 UPDATED: Now passing all 3 arguments required by workflows.py
        args=[container_id, project_id, initial_tags],
        id=workflow_id,
        task_queue="erpnext-inventory-queue"
    )
    return workflow_id

async def get_workflow_handle(container_id: str):
    TEMPORAL_HOST = os.getenv("TEMPORAL_HOST")
    client = await Client.connect(TEMPORAL_HOST)
    return client.get_workflow_handle(f"config-workflow-{container_id}")