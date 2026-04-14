import asyncio
import uuid
import sys
import os
from sqlalchemy import delete

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from shared.database.db import AsyncSessionLocal
from shared.models.is_models import ISSession

async def reset_project(project_id_str: str) -> None:
    try:
        pid = uuid.UUID(project_id_str)
    except ValueError:
        print("❌ Invalid UUID format.")
        sys.exit(1)

    print(f"🗑️ Wiping Implementation System schema for Project: {pid}")
    async with AsyncSessionLocal() as session:
        # Because of ON DELETE CASCADE, dropping the ISSession record will automatically 
        # wipe all connected files, signals, company profiles, field mappings, algorithms, etc!
        stmt = delete(ISSession).where(ISSession.project_id == pid)
        result = await session.execute(stmt)
        await session.commit()
        
        if result.rowcount > 0:
            print(f"✅ Successfully deleted {result.rowcount} session(s) and all cascaded children.")
        else:
            print("⚠️ No implementation sessions found for this project.")

    # Sweep R2 Storage for zombie objects
    from botocore.config import Config
    import boto3
    try:
        s3 = boto3.client(
            "s3",
            endpoint_url=os.getenv("R2_ENDPOINT"),
            aws_access_key_id=os.getenv("R2_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("R2_SECRET_ACCESS_KEY"),
            config=Config(signature_version="s3v4"),
            region_name="auto",
        )
        # Check all known buckets
        for bucket in ["quarantine", "clean-data", "f3next-artifacts"]:
            try:
                paginator = s3.get_paginator('list_objects_v2')
                pages = paginator.paginate(Bucket=bucket)
                deleted_count = 0
                for page in pages:
                    if 'Contents' not in page:
                        continue
                    to_delete = []
                    for obj in page['Contents']:
                        if project_id_str in obj['Key']:
                            to_delete.append({'Key': obj['Key']})
                    
                    if to_delete:
                        s3.delete_objects(Bucket=bucket, Delete={'Objects': to_delete})
                        deleted_count += len(to_delete)
                
                if deleted_count > 0:
                    print(f"🧹 Swept {deleted_count} zombie objects from R2 bucket '{bucket}'")
            except Exception as e:
                pass # Bucket might not exist or no permission
    except Exception as e:
        print(f"⚠️ Failed to sweep R2: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python reset_implementation.py <project_id>")
        sys.exit(1)
        
    asyncio.run(reset_project(sys.argv[1]))
