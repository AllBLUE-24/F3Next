from temporalio.client import Client
from temporalio.exceptions import WorkflowAlreadyStartedError

async def start_or_signal_discovery(project_id: str, user_message: str):
    """
    Starts the Discovery Workflow or signals it if already running.
    """
    client = await Client.connect("127.0.0.1:7233")
    workflow_id = f"discovery-{project_id}"
    
    try:
        # 1. Try to start the workflow for the first time
        await client.start_workflow(
            "DiscoveryChatWorkflow",
            arg={"project_id": project_id, "initial_message": user_message},
            id=workflow_id,
            task_queue="discovery-queue",
        )
        print(f"🚀 Started New Discovery Workflow: {workflow_id}")
        
    except WorkflowAlreadyStartedError:
        # 2. If already running, send the message as a Signal
        handle = client.get_workflow_handle(workflow_id)
        await handle.signal("receive_user_reply", user_message)
        print(f"📨 Signaled Existing Discovery Workflow: {workflow_id}")

    return workflow_id