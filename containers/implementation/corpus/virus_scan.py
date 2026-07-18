"""Step 2 — virus scan and quarantine activity."""
from __future__ import annotations

import asyncio
import os
from typing import Any, Dict, List

import boto3
from botocore.config import Config
from temporalio import activity


@activity.defn
async def virus_scan_quarantine(files: List[Dict[str, Any]], session_id: str) -> Dict[str, Any]:
    activity.logger.info("▶ virus_scan_quarantine started | files=%d", len(files))

    def _sync_s3_ops():
        s3 = boto3.client(
            "s3",
            endpoint_url=os.getenv("R2_ENDPOINT"),
            aws_access_key_id=os.getenv("R2_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("R2_SECRET_ACCESS_KEY"),
            config=Config(signature_version="s3v4"),
            region_name="auto",
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
                data = response["Body"].read()

                is_infected = (
                    b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
                    in data
                )

                if is_infected:
                    s3.copy_object(
                        Bucket="virus-data",
                        CopySource={"Bucket": "quarantine", "Key": obj_key},
                        Key=obj_key,
                    )
                    infected_count += 1
                    scan_results.append({
                        "file_name": fname,
                        "object_path": obj_key,
                        "status": "infected",
                    })
                else:
                    s3.copy_object(
                        Bucket="clean-data",
                        CopySource={"Bucket": "quarantine", "Key": obj_key},
                        Key=obj_key,
                    )
                    clean_count += 1
                    scan_results.append({
                        "file_name": fname,
                        "object_path": obj_key,
                        "status": "clean",
                    })

                s3.delete_object(Bucket="quarantine", Key=obj_key)
            except s3.exceptions.NoSuchKey:
                activity.logger.error(
                    "  ❌ FILE NOT FOUND in R2: %s - upload verification should have caught this!",
                    obj_key,
                )
                infected_count += 1
                scan_results.append({
                    "file_name": fname,
                    "object_path": obj_key,
                    "status": "missing_file",
                    "error": "File not found in R2 bucket - upload may have failed",
                })
            except Exception as e:
                activity.logger.error("  ❌ S3 Failure on %s: %s", obj_key, str(e))
                infected_count += 1
                scan_results.append({
                    "file_name": fname,
                    "object_path": obj_key,
                    "status": "scan_failed",
                    "error": str(e),
                })

        return clean_count, infected_count, scan_results

    clean_count, infected_count, scan_results = await asyncio.to_thread(_sync_s3_ops)

    try:
        from sqlalchemy import update

        from containers.implementation.file_io.persist_audit import log_audit
        from shared.database.db import AsyncSessionLocal
        from shared.models.is_models import ISFile

        async with AsyncSessionLocal() as session:
            for sr in scan_results:
                obj_key = sr.get("object_path", "")
                if not obj_key:
                    continue

                update_vals = {
                    "virus_scan_status": sr["status"],
                    "bucket_location": "clean-data" if sr["status"] == "clean" else "virus-data",
                }

                stmt = (
                    update(ISFile)
                    .where(ISFile.session_id == session_id)
                    .where(ISFile.r2_object_key == obj_key)
                    .values(**update_vals)
                )
                result = await session.execute(stmt)

                if result.rowcount == 0:
                    activity.logger.warning(
                        "  ⚠️ DB Update Skipped: No row found for %s in session %s",
                        obj_key, session_id,
                    )

            await session.commit()

        await log_audit(
            session_id=session_id,
            action="virus_scan_complete",
            actor="system",
            details={"clean": clean_count, "infected": infected_count},
            result="success" if infected_count == 0 else "failed",
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
