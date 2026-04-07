from fastapi import APIRouter, Body
from app.services.deploy_launcher import launch_infra_deployment

router = APIRouter()

@router.post("/infra/deploy")
async def deploy_infra(project_id: str = Body(...), company_name: str = Body(...)):
    """
    Receives the ID from the Frontend (or Interceptor) 
    and forwards it through the Launcher.
    """
    run_id = await launch_infra_deployment(project_id, company_name)
    return {"status": "dispatched", "workflow_id": run_id}