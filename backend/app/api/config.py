from fastapi import APIRouter, HTTPException
# 🔴 UPDATE IMPORT: We need 'start_config_workflow' too
from backend.app.services.config_launcher import get_workflow_handle, start_config_workflow
from pydantic import BaseModel
from typing import Dict, Any, List
from temporalio.client import Client
from temporalio.exceptions import WorkflowAlreadyStartedError
from uuid import UUID # 🟢 Add this import

router = APIRouter()
TEMPORAL_HOST = "localhost:7233"

# --- Pydantic Models ---
class StartPayload(BaseModel):
    container_id: str
    project_id: UUID
    initial_tags: List[str] = [] # e.g. ["#Ind_Manufacturing"]

class AnswerPayload(BaseModel):
    container_id: str
    project_id: str
    answers: Dict[str, Any]

# --- ROUTES ---

# 🔴 NEW ROUTE: This replaces your 'force_start.py' script
@router.post("/config/start")
async def start_config_workflow(payload: StartPayload):
    # 🔴 THE SOLUTION: Explicitly cast the UUID object to a string
    # This ensures Temporal doesn't try to serialize the object itself
    project_id_str = str(payload.project_id)
    container_id = payload.container_id   

    initial_tags = payload.initial_tags if payload.initial_tags else []

    client = await Client.connect(TEMPORAL_HOST)
    workflow_id = f"config-workflow-{container_id}"

# 🔴 THE "PAST SOLUTION": Programmatic Termination
    # Before starting, we check if a zombie exists and kill it to ensure a fresh run.
    try:
        handle = client.get_workflow_handle(workflow_id)
        # Terminate will stop the workflow if it's Running, Pulsing, or stuck in Retries
        await handle.terminate("Restarting via UI trigger")
        print(f"💀 Terminated existing zombie: {workflow_id}")
    except Exception:
        # If it doesn't exist, we just move on
        pass

    try:
        print(f"🚀 Launching Fresh Workflow: {workflow_id}")
        await client.start_workflow(
            "ConfigWorkflow",
            args=[container_id, project_id_str, initial_tags], 
            id=workflow_id,
            task_queue="erpnext-inventory-queue"
        )
        return {"status": "started", "workflow_id": workflow_id}
    except Exception as e:
        print(f"❌ Fatal Start Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/config/{container_id}/status")
async def get_config_status(container_id: str):
    print(f"🔎 API: Checking status for {container_id}...")
    try:
        client = await Client.connect(TEMPORAL_HOST)
        handle = client.get_workflow_handle(f"config-workflow-{container_id}")
        
        # We must check if the workflow is actually running before querying
        desc = await handle.describe()
        if desc.status != 1: # 1 = RUNNING
             return {"status": "NOT_STARTED", "questions": [], "current_layer": 0}

        state = await handle.query("get_state")
        return state
        
    except Exception as e:
        # 🔴 EXACT FIX: Return an object the Frontend can understand
        return {"status": "NOT_STARTED", "questions": [], "current_layer": 0}


@router.post("/config/answer")
async def submit_answers(payload: AnswerPayload):
    try:
        client = await Client.connect(TEMPORAL_HOST)
        handle = client.get_workflow_handle(f"config-workflow-{payload.container_id}")
        
        # 🔴 EXACT FIX: Verify workflow is alive before signaling
        try:
            await handle.describe()
        except Exception:
            raise HTTPException(status_code=400, detail="Configuration agent is not active. Please refresh.")

        await handle.signal("submit_answers_signal", payload.answers)
        return {"status": "accepted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))