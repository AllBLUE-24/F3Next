from temporalio.client import Client
# 🟢 Import the specific exception
from temporalio.exceptions import WorkflowAlreadyStartedError

TEMPORAL_HOST = "localhost:7233"

async def launch_config_apply_agent(project_id: str) -> str:
    """
    Service: Connects to Temporal and triggers the ConfigApplyWorkflow.
    If already running, returns the existing Run ID.
    """
    print(f"🚀 SERVICE: Launching Config-Apply Agent for Project {project_id}...")
    
    client = await Client.connect(TEMPORAL_HOST)
    workflow_id = f"apply-{project_id}"

    try:
        # Try to start a fresh workflow
        handle = await client.start_workflow(
            "ConfigApplyWorkflow",
            args=[project_id],
            id=workflow_id,
            task_queue="erpnext-apply-queue"
        )
        print(f"✅ SERVICE: Started NEW workflow: {handle.result_run_id}")
        return handle.result_run_id

    except WorkflowAlreadyStartedError:
        # 🟢 HANDLED: If it's already running, get the existing handle
        print(f"⚠️ SERVICE: Workflow {workflow_id} is already running. Connecting to existing instance...")
        handle = client.get_workflow_handle(workflow_id)
        
        # Optional: verify it is actually running
        desc = await handle.describe()
        print(f"ℹ️ Existing Run ID: {desc.run_id}")
        return desc.run_id