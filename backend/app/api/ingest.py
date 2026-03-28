from typing import List
from fastapi import APIRouter, UploadFile, File, Header
from datetime import datetime
import uuid

from shared.database.minio import minio_client, ensure_bucket, MINIO_BUCKET

router = APIRouter(tags=["Ingestion"])

@router.post("/ingest")
async def ingest_files(
    files: List[UploadFile] = File(...),
    x_company_slug: str = Header(...),
    x_user_slug: str = Header(...),
):
    ensure_bucket()

    uploaded_files = []

    for file in files:
        file.file.seek(0)

        object_name = (
            f"clients/{x_company_slug}/"
            f"users/{x_user_slug}/"
            f"ingestion/raw/"
            f"{datetime.utcnow():%Y/%m/%d}/"
            f"{uuid.uuid4()}_{file.filename}"
        )

        minio_client.put_object(
            bucket_name=MINIO_BUCKET,
            object_name=object_name,
            data=file.file,
            length=-1,
            part_size=10 * 1024 * 1024,
            content_type=file.content_type or "application/octet-stream",
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