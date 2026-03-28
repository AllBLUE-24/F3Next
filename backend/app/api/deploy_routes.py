from fastapi import APIRouter, HTTPException
import os
from dotenv import load_dotenv
load_dotenv()

from pydantic import BaseModel
from temporalio.client import Client

router = APIRouter(prefix="/deploy", tags=["Infrastructure"])

# Define what the Frontend sends
class InfraRequest(BaseModel):
    project_id: str
    company_slug: str
    tier: str = "standard"  # Default to standard

@router.post("/infra")
async def trigger_infra_deployment(payload: InfraRequest):
    """
    Receives JSON from Frontend -> Starts Temporal Workflow
    """
    try:
        # 1. Connect to Temporal
        client = await Client.connect(os.getenv("TEMPORAL_HOST"))

        # 2. Prepare Workflow Input
        workflow_input = {
            "project_id": payload.project_id,
            "company_slug": payload.company_slug,
            "tier": payload.tier
        }

        # 3. Start the Workflow
        handle = await client.start_workflow(
            "ERPNextProvisioningWorkflow",
            workflow_input,
            id=f"provision-{payload.project_id}", # Deduplication ID
            task_queue="erpnext-provisioning-queue",
        )

        return {
            "status": "triggered",
            "workflow_id": handle.id,
            "message": "Infrastructure provisioning started."
        }

    except Exception as e:
        print(f"❌ Error triggering workflow: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))