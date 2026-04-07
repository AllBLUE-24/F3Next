"""
Tri-Bucket Virus Scanning Activity.

Safely extracts binary data streams directly from the frontend's 'quarantine' R2 bucket.
Performs real-time heuristic scanning.
Legitimate files are duplicated to 'clean-data'.
Infected payloads are shunted to 'virus-data'.
"""

import os
import boto3
from botocore.config import Config
from temporalio import activity
from typing import List, Dict, Any

@activity.defn
def virus_scan_quarantine(files: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Receives list of file object dictionaries from Workflow Signal.
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

    for file_info in files:
        obj_key = file_info.get("object_path")
        if not obj_key:
            activity.logger.warning("  ⚠️ Skipping file entry with no object_path: %s", file_info)
            continue
            
        # 1. Pipeline binary payload from S3 to memory
        try:
            response = s3.get_object(Bucket="quarantine", Key=obj_key)
            data = response['Body'].read()
            
            # --- Mock ClamAV Validation Heuristics ---
            # Standard EICAR string detection for safe virus testing
            is_infected = b'X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*' in data
            
            if is_infected:
                activity.logger.warning("  🚨 INFECTED PAYLOAD DETECTED: %s", obj_key)
                # Shunt to permanent quarantine
                s3.copy_object(
                    Bucket="virus-data",
                    CopySource={"Bucket": "quarantine", "Key": obj_key},
                    Key=obj_key
                )
                infected_count += 1
            else:
                # Mirror strictly to secure infrastructure
                s3.copy_object(
                    Bucket="clean-data",
                    CopySource={"Bucket": "quarantine", "Key": obj_key},
                    Key=obj_key
                )
                clean_count += 1
                
            # Eradicate original unsafe ingestion
            s3.delete_object(Bucket="quarantine", Key=obj_key)
            
        except Exception as e:
            activity.logger.error("  ❌ S3 Stream Failure on %s: %s", obj_key, str(e))
            infected_count += 1  # Assume unsafe if unparseable

    activity.logger.info("✅ virus_scan_quarantine done | scanned=%d infected=%d",
                         clean_count + infected_count, infected_count)
    return {
        "safe": infected_count == 0,
        "clean_count": clean_count,
        "infected_count": infected_count
    }
