from fastapi import APIRouter, HTTPException
# 🔴 UPDATE IMPORT: We need 'start_config_workflow' too
from backend.app.services.config_launcher import get_workflow_handle, start_config_workflow
from pydantic import BaseModel
from typing import Dict, Any, List
from temporalio.client import Client
from temporalio.exceptions import WorkflowAlreadyStartedError

router = APIRouter()
TEMPORAL_HOST = "localhost:7233"

# --- Pydantic Models ---
class StartPayload(BaseModel):
    container_id: str
    project_id: str
    initial_tags: List[str] # e.g. ["#Ind_Manufacturing"]

class AnswerPayload(BaseModel):
    container_id: str
    project_id: str
    answers: Dict[str, Any]

# --- ROUTES ---

# 🔴 NEW ROUTE: This replaces your 'force_start.py' script
@router.post("/config/start")
async def start_config(payload: StartPayload):
    # The Frontend calls /resolve/slug/..., gets the project UUID, 
    # and passes it here.
    
    # Validation: Ensure it's a valid UUID (Optional but good safety)
    try:
        # Just checking if it's 36 chars or looks like UUID
        if len(payload.project_id) < 32:
             raise ValueError("Invalid Project ID format")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Project ID (Must be UUID)")

    print(f"🚀 Starting Workflow for Project {payload.project_id}")
    
    try:
        run_id = await start_config_workflow(
            payload.container_id, 
            payload.project_id,  # <--- Pass the dynamic ID
            payload.initial_tags
        )
        return {"status": "started", "run_id": run_id}
    except WorkflowAlreadyStartedError:
        return {"status": "already_running"}

        
@router.get("/config/{container_id}/status")
async def get_config_status(container_id: str):
    # --- DEBUG MODE ---
    print(f"🔎 API: Checking status for {container_id}...")
    
    try:
        client = await Client.connect(TEMPORAL_HOST)
        handle = client.get_workflow_handle(f"config-workflow-{container_id}")
        
        state = await handle.query("get_state")
        return state
        
    except Exception as e:
        # If workflow doesn't exist yet, return a specific status so Frontend knows to call /start
        print(f"⚠️ Status check failed (Workflow might not exist): {e}")
        return {"status": "NOT_STARTED", "details": str(e)}

@router.post("/config/answer")
async def submit_answers(payload: AnswerPayload):
    try:
        client = await Client.connect(TEMPORAL_HOST)
        handle = client.get_workflow_handle(f"config-workflow-{payload.container_id}")
        
        await handle.signal("submit_answers_signal", payload.answers)
        return {"status": "accepted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))