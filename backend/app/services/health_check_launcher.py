import os
from temporalio.client import Client
from containers.health_check.workflows import HealthCheckWorkflow
from temporalio.exceptions import WorkflowAlreadyStartedError

async def start_health_check_flow(uid: str, answers: dict, project_id: str):
    # Connect to the temporal service in the docker network
    temporal_url = os.getenv("TEMPORAL_URL", "127.0.0.1:7233")
    client = await Client.connect(temporal_url)
    workflow_id = f"hc-verify-{uid}"
    # Start the workflow
    try:
        handle = await client.start_workflow(
            "HealthCheckWorkflow",
            arg={"answers": answers, "project_id": project_id},
            id=workflow_id,
            task_queue="health-check-queue",
        )
        return workflow_id

    except WorkflowAlreadyStartedError:    
    
# Instead of crashing, just return the ID of the one already running
        print(f"⚠️ Workflow {workflow_id} already in progress. Re-attaching...")
        return workflow_id