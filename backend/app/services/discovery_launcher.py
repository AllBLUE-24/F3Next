import uuid
from uuid import UUID
from temporalio.client import Client
from temporalio.exceptions import WorkflowAlreadyStartedError
from sqlalchemy import select
from shared.database.db import AsyncSessionLocal
from shared.models.hooks import Hook

async def start_or_signal_discovery(project_id: str, user_message: str):
    """
    Starts the Discovery Workflow or signals it if already running.
    Ensures the 'hooks' DB row exists before starting.
    """
    pid = UUID(project_id) if isinstance(project_id, str) else project_id

    # ---------------------------------------------------------
    # 1. CRITICAL FIX: Ensure DB Row Exists
    # ---------------------------------------------------------
    async with AsyncSessionLocal() as db:
        # Check if the row exists (use UUID for SQLite Uuid column)
        result = await db.execute(select(Hook).where(Hook.project_id == pid))
        existing_hook = result.scalar_one_or_none()
        
        if not existing_hook:
            print(f"[Discovery] Creating new Hook row for {project_id}")
            # Create the initial row
            new_hook = Hook(
                project_id=pid, 
                discovery_status="STARTING",
                discovery_step=1,
                extracted_tags=[], 
                last_bot_response="Thinking...",
                
                # --- 🔥 THE FIX IS HERE ---
                # We must provide an empty value to satisfy the NOT NULL constraint
                answers_health_check={}, 
                report_content="" 
                # --------------------------
            )
            db.add(new_hook)
            await db.commit()
    # ---------------------------------------------------------

    client = await Client.connect("127.0.0.1:7233")
    workflow_id = f"discovery-{project_id}"
    
    try:
        # 2. Try to start the workflow for the first time
        await client.start_workflow(
            "DiscoveryChatWorkflow",
            arg={"project_id": project_id, "initial_message": user_message},
            id=workflow_id,
            task_queue="discovery-queue",
        )
        print(f"[Discovery] Started new workflow: {workflow_id}")
        
    except WorkflowAlreadyStartedError:
        # 3. If already running, send the message as a Signal
        handle = client.get_workflow_handle(workflow_id)
        await handle.signal("receive_user_reply", user_message)
        print(f"[Discovery] Signaled existing workflow: {workflow_id}")

    return workflow_id