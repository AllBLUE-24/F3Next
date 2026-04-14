import os
import asyncio
from datetime import datetime
from typing import List, Dict, Any

import boto3
from botocore.config import Config
from temporalio import activity

@activity.defn
async def virus_scan_quarantine(files: List[Dict[str, Any]], session_id: str) -> Dict[str, Any]:
    activity.logger.info("▶ virus_scan_quarantine started | files=%d", len(files))

    # 1. Run blocking S3 operations in a safe background thread
    def _sync_s3_ops():
        s3 = boto3.client(
            "s3",
            endpoint_url=os.getenv("R2_ENDPOINT"),
            aws_access_key_id=os.getenv("R2_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("R2_SECRET_ACCESS_KEY"),
            config=Config(signature_version="s3v4"),
            region_name="auto"
        )
        clean_count = 0
        infected_count = 0
        scan_results = []

        for file_info in files:
            obj_key = file_info.get("object_path")
            fname = file_info.get("file_name", "")
            if not obj_key:
                continue

            try:
                response = s3.get_object(Bucket="quarantine", Key=obj_key)
                data = response['Body'].read()

                # Mock ClamAV Validation Heuristics
                is_infected = b'X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*' in data

                if is_infected:
                    s3.copy_object(Bucket="virus-data", CopySource={"Bucket": "quarantine", "Key": obj_key}, Key=obj_key)
                    infected_count += 1
                    scan_results.append({"file_name": fname, "object_path": obj_key, "status": "infected"})
                else:
                    s3.copy_object(Bucket="clean-data", CopySource={"Bucket": "quarantine", "Key": obj_key}, Key=obj_key)
                    clean_count += 1
                    scan_results.append({"file_name": fname, "object_path": obj_key, "status": "clean"})

                s3.delete_object(Bucket="quarantine", Key=obj_key)
            except Exception as e:
                activity.logger.error("  ❌ S3 Failure on %s: %s", obj_key, str(e))
                infected_count += 1
                scan_results.append({"file_name": fname, "object_path": obj_key, "status": "scan_failed"})

        return clean_count, infected_count, scan_results

    # Await the thread so we don't block Temporal
    clean_count, infected_count, scan_results = await asyncio.to_thread(_sync_s3_ops)

    # 2. Safely perform Async Database Updates
    try:
        from shared.database.db import AsyncSessionLocal
        from shared.models.is_models import ISFile
        from sqlalchemy import select, update
        from containers.implementation.file_io.persist_audit import log_audit

        async with AsyncSessionLocal() as session:
            for sr in scan_results:
                obj_key = sr.get("object_path", "")
                if not obj_key:
                    continue

                # Query using the exact column name from your DB
                stmt = select(ISFile).where(ISFile.r2_object_key == obj_key)
                result = await session.execute(stmt)
                file_row = result.scalar_one_or_none()

                if not file_row:
                    activity.logger.warning("  ⚠️ DB Update Skipped: No row found for %s", obj_key)
                    continue

                # Update the exact columns that exist in your DB
                update_vals = {
                    "virus_scan_status": sr["status"],
                    "bucket_location": "clean-data" if sr["status"] == "clean" else "virus-data"
                }

                await session.execute(update(ISFile).where(ISFile.id == file_row.id).values(**update_vals))
            
            await session.commit()

        # Add the audit log
        await log_audit(
            session_id=session_id,
            action="virus_scan_complete",
            actor="system",
            details={"clean": clean_count, "infected": infected_count},
            result="success" if infected_count == 0 else "failed"
        )
        activity.logger.info("  ✅ is_files and is_audit_trail updated")

    except Exception as e:
        activity.logger.error("  ❌ DB update failed: %s", e)

    return {
        "safe": infected_count == 0,
        "clean_count": clean_count,
        "infected_count": infected_count,
        "scan_results": scan_results,
    }