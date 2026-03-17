from fastapi import APIRouter, Body
from backend.app.services.workflow_launcher import launcher

router = APIRouter()

@router.post("/infra/deploy")
async def deploy_infra(project_id: str = Body(...), company_name: str = Body(...)):
    """
    Receives the ID from the Frontend (or Interceptor) 
    and forwards it through the Launcher.
    """
    # Forwarding to the Workflow Launcher
    run_id = await launcher.launch_agent(
        workflow_name="InfraDeploymentWorkflow",
        project_id=project_id,
        task_queue="infra-agent-queue",
        company_name=company_name
    )
    return {"status": "dispatched", "workflow_id": run_id}