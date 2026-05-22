import uuid
import os
from dotenv import load_dotenv
load_dotenv()

from uuid import UUID
from temporalio.client import Client
from temporalio.exceptions import WorkflowAlreadyStartedError
from temporalio.service import RPCError
from sqlalchemy import select
from shared.database.db import AsyncSessionLocal
from shared.models.hooks import Hook

async def start_or_signal_discovery(project_id: str, user_message: str):
    """
    Starts the Discovery Workflow or signals it if already running.
    
    Key logic:
    - If DB status is "START" (reset was run), terminate any stale Temporal workflow
      and start fresh.
    - If a workflow is already running and DB is not reset, signal the existing workflow.
    - Ensures the 'hooks' DB row exists before starting.
    """
    pid = UUID(project_id) if isinstance(project_id, str) else project_id

    # ---------------------------------------------------------
    # 1. Ensure DB Row Exists + Check if DB was Reset
    # ---------------------------------------------------------
    db_was_reset = False
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Hook).where(Hook.project_id == pid))
        existing_hook = result.scalar_one_or_none()

        if not existing_hook:
            print(f"[Discovery] Creating new Hook row for {project_id}")
            new_hook = Hook(
                project_id           = pid,
                discovery_status     = "STARTING",
                discovery_step       = 1,
                discovery_turn_count = 0,
                discovery_coverage   = {
                    "industry":      {"status": None, "value": None},
                    "strategy":      {"status": None, "value": None},
                    "scale":         {"status": None, "value": None},
                    "legacy_system": {"status": None, "value": None},
                    "pain_point":    {"status": None, "value": None},
                },
                extracted_tags       = [],
                last_bot_response    = "Thinking...",
                answers_health_check = {},
                report_content       = "",
            )
            db.add(new_hook)
            await db.commit()
        else:
            # If the DB was reset (status=START), we need to restart the Temporal workflow
            if existing_hook.discovery_status == "START":
                db_was_reset = True
                print(f"[Discovery] DB status is START (was reset) — will force-restart workflow for {project_id}")

    # ---------------------------------------------------------
    # 2. Connect to Temporal + handle workflow lifecycle
    # ---------------------------------------------------------
    client = await Client.connect(os.getenv("TEMPORAL_HOST", "localhost:7233"))
    workflow_id = f"discovery-{project_id}"

    if db_was_reset:
        # Terminate any stale workflow before starting fresh
        try:
            handle = client.get_workflow_handle(workflow_id)
            await handle.terminate(reason="Discovery session reset by user")
            print(f"[Discovery] Terminated stale workflow: {workflow_id}")
        except RPCError:
            # Workflow not found or already closed — fine
            pass
        except Exception as e:
            print(f"[Discovery] Warning: could not terminate stale workflow: {e}")

    try:
        # Start fresh workflow
        await client.start_workflow(
            "DiscoveryChatWorkflow",
            arg={"project_id": project_id, "initial_message": user_message},
            id=workflow_id,
            task_queue="discovery-queue",
        )
        print(f"[Discovery] Started new workflow: {workflow_id}")

    except WorkflowAlreadyStartedError:
        if db_was_reset:
            # This shouldn't happen after terminate, but handle it gracefully
            print(f"[Discovery] Warning: workflow still running after terminate attempt — signaling instead")
        # Signal the existing running workflow with the user's message
        handle = client.get_workflow_handle(workflow_id)
        await handle.signal("receive_user_reply", user_message)
        print(f"[Discovery] Signaled existing workflow: {workflow_id}")

    return workflow_id