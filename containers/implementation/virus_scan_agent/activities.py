"""
Tri-Bucket Virus Scanning Activity.

Safely extracts binary data streams directly from the frontend's 'quarantine' R2 bucket.
Performs real-time heuristic scanning.
Legitimate files are duplicated to 'clean-data'.
Infected payloads are shunted to 'virus-data'.

v2: Updates is_files rows with clean_r2_path, virus_r2_path, scan status, and timestamps.
"""

import os
import uuid
from datetime import datetime
from typing import List, Dict, Any

import boto3
from botocore.config import Config
from temporalio import activity


@activity.defn
def virus_scan_quarantine(files: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Receives list of file object dictionaries from Workflow Signal.
    Scans each file, routes to clean-data or virus-data bucket.
    Updates is_files table with results.
    """
    activity.logger.info("▶ virus_scan_quarantine started | files=%d", len(files))

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
    scan_results: List[Dict[str, Any]] = []

    for file_info in files:
        obj_key = file_info.get("object_path")
        fname = file_info.get("file_name", "")
        if not obj_key:
            activity.logger.warning("  ⚠️ Skipping file entry with no object_path: %s", file_info)
            continue

        # 1. Pipeline binary payload from S3 to memory
        try:
            response = s3.get_object(Bucket="quarantine", Key=obj_key)
            data = response['Body'].read()
            file_size = len(data)

            # --- Mock ClamAV Validation Heuristics ---
            is_infected = b'X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*' in data

            if is_infected:
                activity.logger.warning("  🚨 INFECTED PAYLOAD DETECTED: %s", obj_key)
                s3.copy_object(
                    Bucket="virus-data",
                    CopySource={"Bucket": "quarantine", "Key": obj_key},
                    Key=obj_key
                )
                infected_count += 1
                scan_results.append({
                    "file_name": fname,
                    "object_path": obj_key,
                    "status": "infected",
                    "virus_r2_path": obj_key,
                    "file_size_bytes": file_size,
                })
            else:
                s3.copy_object(
                    Bucket="clean-data",
                    CopySource={"Bucket": "quarantine", "Key": obj_key},
                    Key=obj_key
                )
                clean_count += 1
                scan_results.append({
                    "file_name": fname,
                    "object_path": obj_key,
                    "status": "clean",
                    "clean_r2_path": obj_key,
                    "file_size_bytes": file_size,
                })

            # Eradicate original unsafe ingestion
            s3.delete_object(Bucket="quarantine", Key=obj_key)

        except Exception as e:
            activity.logger.error("  ❌ S3 Stream Failure on %s: %s", obj_key, str(e))
            infected_count += 1  # Assume unsafe if unparseable
            scan_results.append({
                "file_name": fname,
                "object_path": obj_key,
                "status": "scan_failed",
                "file_size_bytes": 0,
            })

    # ── Persist scan results to is_files table ──────────────────────────────
    try:
        from shared.database.db import AsyncSessionLocal
        from shared.models.is_models import ISFile
        from sqlalchemy import select, update
        import asyncio

        async def _persist():
            async with AsyncSessionLocal() as session:
                for sr in scan_results:
                    obj_key = sr.get("object_path", "")
                    if not obj_key:
                        continue
                    # Find the file row by quarantine_r2_path
                    stmt = select(ISFile).where(ISFile.quarantine_r2_path == obj_key)
                    result = await session.execute(stmt)
                    file_row = result.scalar_one_or_none()
                    if not file_row:
                        continue

                    update_vals = {
                        "virus_scan_status": sr["status"],
                        "file_size_bytes": sr.get("file_size_bytes", 0),
                        "scanned_at": datetime.utcnow(),
                        "virus_scan_details": {"scanner": "heuristic_mock_clamav"},
                    }
                    if sr["status"] == "clean":
                        update_vals["clean_r2_path"] = sr.get("clean_r2_path")
                    elif sr["status"] == "infected":
                        update_vals["virus_r2_path"] = sr.get("virus_r2_path")

                    await session.execute(
                        update(ISFile).where(ISFile.id == file_row.id).values(**update_vals)
                    )
                await session.commit()

        # Run async persistence from sync context
        asyncio.run(_persist())
        activity.logger.info("  ✅ is_files updated with scan results")
    except Exception as e:
        activity.logger.error("  ❌ is_files DB update failed: %s", e)

    activity.logger.info("✅ virus_scan_quarantine done | scanned=%d infected=%d",
                         clean_count + infected_count, infected_count)
    return {
        "safe": infected_count == 0,
        "clean_count": clean_count,
        "infected_count": infected_count,
        "scan_results": scan_results,
    }
