from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
# Import the launcher service we just created
from app.services.config_apply_launcher import launch_config_apply_agent

router = APIRouter(tags=["Config Apply Agent"])

class StartAgentRequest(BaseModel):
    project_id: str

@router.post("/config_apply/start")
async def start_config_apply(payload: StartAgentRequest):
    """
    Frontend calls this endpoint. We delegate to the Service Launcher.
    """
    try:
        run_id = await launch_config_apply_agent(payload.project_id)
        return {"status": "success", "run_id": run_id}
    except Exception as e:
        print(f"❌ API ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to launch agent")