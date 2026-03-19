from typing import List
from fastapi import APIRouter, UploadFile, File, HTTPException, Header
from datetime import datetime
import uuid

from app.core.storage import USE_LOCAL_STORAGE, store_file_local

router = APIRouter(tags=["Ingestion"])


def _store_file(file: UploadFile, object_name: str) -> None:
    """Store file using local disk (no Docker/Minio required)."""
    file.file.seek(0)
    store_file_local(
        object_name,
        file.file,
        content_type=file.content_type or "application/octet-stream",
    )


@router.post("/ingest")
async def ingest_files(
    files: List[UploadFile] = File(...),
    x_company_slug: str = Header(...),
    x_user_slug: str = Header(...),
):
    uploaded_files = []

    for file in files:
        object_name = (
            f"clients/{x_company_slug}/"
            f"users/{x_user_slug}/"
            f"ingestion/raw/"
            f"{datetime.utcnow():%Y/%m/%d}/"
            f"{uuid.uuid4()}_{file.filename}"
        )

        if USE_LOCAL_STORAGE:
            _store_file(file, object_name)
        else:
            from app.core.minio import minio_client, ensure_bucket, MINIO_BUCKET
            ensure_bucket()
            file.file.seek(0)
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
        "storage": "local" if USE_LOCAL_STORAGE else "minio",
    }
