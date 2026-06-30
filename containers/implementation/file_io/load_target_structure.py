"""
File IO Agent — Load target structure from is_target_structures table.

Used by IS workflow Step 8 to check if target was pre-generated post-discovery.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict
from uuid import UUID
import json

from temporalio import activity
from sqlalchemy import select

from shared.database.db import AsyncSessionLocal
from shared.models.is_models import ISTargetStructure


@dataclass
class LoadTargetStructureInput:
    session_id: str


@activity.defn(name="load_target_structure")
async def load_target_structure(inp: LoadTargetStructureInput) -> Dict[str, Any]:
    """
    Load target structure from is_target_structures table + R2.
    
    Returns:
        Dict with:
        - required_doctypes: list
        - setup_steps: list
        - import_phases: dict
        - seed_doctypes: list
        - deferred_doctypes: list
        - exists: bool (True if found, False otherwise)
    """
    activity.logger.info("▶ load_target_structure | session_id=%s", inp.session_id)
    
    try:
        async with AsyncSessionLocal() as db:
            stmt = (
                select(ISTargetStructure)
                .where(ISTargetStructure.session_id == UUID(inp.session_id))
                .order_by(ISTargetStructure.created_at.desc())
                .limit(1)
            )
            row = (await db.execute(stmt)).scalar_one_or_none()
            
            if not row:
                activity.logger.info("  ⚠️ No target structure found for session %s", inp.session_id)
                return {"exists": False}
            
            # Parse JSON fields
            required = row.required_doctypes
            if isinstance(required, str):
                required = json.loads(required)
            
            steps = row.setup_steps
            if isinstance(steps, str):
                steps = json.loads(steps)
            
            phases = row.import_phases
            if isinstance(phases, str):
                phases = json.loads(phases)
            
            result = {
                "required_doctypes": required or [],
                "setup_steps": steps or [],
                "import_phases": phases or {},
                "seed_doctypes": [],
                "deferred_doctypes": [],
                "exists": True,
                "r2_path": row.r2_path,
                "f3iche": row.f3iche,
                "total_doctypes": row.total_doctypes,
            }
            
            # Try to load seed_doctypes and deferred_doctypes from R2
            if row.r2_path:
                try:
                    import boto3
                    import os
                    
                    s3 = boto3.client(
                        "s3",
                        endpoint_url=os.getenv("R2_ENDPOINT"),
                        aws_access_key_id=os.getenv("R2_ACCESS_KEY_ID"),
                        aws_secret_access_key=os.getenv("R2_SECRET_ACCESS_KEY"),
                        region_name="auto",
                    )
                    
                    response = s3.get_object(Bucket="clean-data", Key=row.r2_path)
                    r2_data = json.loads(response["Body"].read().decode("utf-8"))
                    
                    result["seed_doctypes"] = r2_data.get("seed_doctypes", [])
                    result["deferred_doctypes"] = r2_data.get("deferred_doctypes", [])
                    
                    activity.logger.info("  ✅ Target structure loaded from R2: %s", row.r2_path)
                except Exception as e:
                    activity.logger.warning("  ⚠️ Could not load R2 data: %s", e)
            
            activity.logger.info("  ✅ Target structure loaded | %d doctypes, %d steps", 
                                len(result["required_doctypes"]), len(result["setup_steps"]))
            
            return result
    
    except Exception as e:
        activity.logger.error("  ❌ Failed to load target structure: %s", e)
        return {"exists": False, "error": str(e)}
