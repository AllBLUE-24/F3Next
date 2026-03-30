from typing import List
from fastapi import APIRouter, UploadFile, File, Header
from datetime import datetime
import uuid

from shared.database.s3 import s3_client, S3_BUCKET

router = APIRouter(tags=["Ingestion"])

@router.post("/ingest")
async def ingest_files(
    files: List[UploadFile] = File(...),
    x_company_slug: str = Header(...),
    x_user_slug: str = Header(...),
):
    uploaded_files = []

    for file in files:
        # Read file into memory for boto3 payload
        file_bytes = file.file.read()

        object_name = (
            f"clients/{x_company_slug}/"
            f"users/{x_user_slug}/"
            f"ingestion/raw/"
            f"{datetime.utcnow():%Y/%m/%d}/"
            f"{uuid.uuid4()}_{file.filename}"
        )

        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=object_name,
            Body=file_bytes,
            ContentType=file.content_type or "application/octet-stream",
        )

        uploaded_files.append({
            "file_name": file.filename,
            "object_path": object_name,
        })

    return {
        "status": "success",
        "client": x_company_slug,
        "user": x_user_slug,
        "count": len(uploaded_files),
        "files": uploaded_files,
    }