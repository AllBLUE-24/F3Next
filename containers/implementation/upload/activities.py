import os
import asyncio
from dataclasses import dataclass
from typing import Dict, Any

import boto3
from botocore.config import Config
from temporalio import activity
from dotenv import load_dotenv

# Load environment variables from the root .env file
load_dotenv()

@dataclass
class UploadFileInput:
    project_id: str
    file_name: str
    file_content: bytes
    content_type: str


def _upload_to_r2_sync(inp: UploadFileInput) -> Dict[str, Any]:
    """
    Synchronous boto3 call to upload the file to Cloudflare R2.
    """
    # Cloudflare R2 uses the S3 API
    s3_client = boto3.client(
        "s3",
        endpoint_url=os.getenv("R2_ENDPOINT"),
        aws_access_key_id=os.getenv("R2_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("R2_SECRET_ACCESS_KEY"),
        config=Config(signature_version="s3v4"),
        region_name="auto"  # R2 ignores region, but boto3 often requires it to be set
    )

    bucket_name = "quarantine"
    
    # Organize files in the bucket by project_id
    object_key = f"{inp.project_id}/{inp.file_name}"

    # Perform the upload
    s3_client.put_object(
        Bucket=bucket_name,
        Key=object_key,
        Body=inp.file_content,
        ContentType=inp.content_type
    )

    return {
        "status": "success",
        "bucket": bucket_name,
        "object_key": object_key,
        "file_name": inp.file_name
    }


@activity.defn(name="upload_file_to_quarantine")
async def upload_file_to_quarantine(inp: UploadFileInput) -> Dict[str, Any]:
    """
    Temporal Activity: Uploads a raw file payload to the R2 quarantine bucket.
    Uses asyncio.to_thread to prevent the synchronous boto3 call from blocking 
    the Temporal worker's event loop.
    """
    try:
        # Run the blocking boto3 network call in a separate thread
        result = await asyncio.to_thread(_upload_to_r2_sync, inp)
        return result
    except Exception as exc:
        # Temporal will automatically catch and retry based on your RetryPolicy
        raise RuntimeError(f"Failed to upload {inp.file_name} to R2: {str(exc)}")