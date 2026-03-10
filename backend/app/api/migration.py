import boto3
import os
import json
from pathlib import Path
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from botocore.exceptions import ClientError
from temporalio.client import Client

# Import your launcher
from app.services.migration_launcher import launch_legacy_migration_workflow

# 1. LOAD ENV VARS
env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

router = APIRouter()

# 2. VALIDATE CONFIGURATION
S3_BUCKET = os.getenv("S3_BUCKET_NAME")
if not S3_BUCKET:
    raise RuntimeError("CRITICAL: S3_BUCKET_NAME is missing in .env file!")

REGION = os.getenv("AWS_REGION", "ap-south-1")
TEMPORAL_HOST = os.getenv("TEMPORAL_HOST", "localhost:7233")

s3_client = boto3.client(
    "s3",
    region_name=REGION,
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
)

# --- MODELS ---
class UploadRequest(BaseModel):
    filename: str
    file_type: str
    company_slug: str

class StartMigrationRequest(BaseModel):
    file_key: str
    company_slug: str
    project_id: str

class ConfirmMappingRequest(BaseModel):
    workflow_id: str
    approved_mapping: dict
    project_id: str

# --- ENDPOINT 1: Get Secure Upload URL ---
@router.post("/migration/get-upload-url")
async def generate_upload_url(data: UploadRequest):
    try:
        object_name = f"uploads/{data.company_slug}/raw_backups/{data.filename}"
        presigned_url = s3_client.generate_presigned_url(
            'put_object',
            Params={'Bucket': S3_BUCKET, 'Key': object_name, 'ContentType': data.file_type},
            ExpiresIn=300
        )
        return {"upload_url": presigned_url, "file_key": object_name}
    except ClientError as e:
        raise HTTPException(status_code=500, detail="Could not generate upload URL")

# --- ENDPOINT 2: Trigger Workflow ---
@router.post("/migration/start-analysis")
async def start_analysis(data: StartMigrationRequest):
    try:
        workflow_id = await launch_legacy_migration_workflow(
            company_slug=data.company_slug,
            s3_file_key=data.file_key
        )
        return {"status": "started", "workflow_id": workflow_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- ENDPOINT 3: Check Status (THIS WAS MISSING) ---
@router.get("/migration/status/{workflow_id}")
async def get_migration_status(workflow_id: str):
    """
    Frontend polls this to check if AI analysis is done.
    """
    try:
        client = await Client.connect(TEMPORAL_HOST)
        handle = client.get_workflow_handle(workflow_id)
        
        # Query the running workflow for its state
        # Note: This relies on the 'get_current_proposal' query we added to workflows.py
        proposal = await handle.query("get_current_proposal")
        
        if proposal:
             return {"status": "ready_for_review", "proposal": proposal}
        else:
             return {"status": "processing"}

    except Exception as e:
        # If workflow isn't found or query fails, just return waiting
        print(f"Status check error: {e}")
        return {"status": "processing"}

# --- ENDPOINT 4: Confirm Mapping (THIS WAS MISSING) ---
@router.post("/migration/confirm-mapping")
async def confirm_mapping(data: ConfirmMappingRequest):
    try:
        client = await Client.connect(TEMPORAL_HOST)
        handle = client.get_workflow_handle(data.workflow_id)
        
        # Send the signal to unblock the workflow
        await handle.signal("submit_mapping_correction", data.approved_mapping)
        
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))