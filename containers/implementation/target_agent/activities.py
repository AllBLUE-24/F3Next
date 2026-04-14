"""
Target Agent — Temporal activities for building the ERPNext action workflow.
"""
from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass
from typing import Any, Dict

import boto3
from botocore.config import Config
from sqlalchemy import select
from temporalio import activity

from shared.database.db import AsyncSessionLocal
from shared.models.is_models import ISCompanyProfile, ISTargetStructure
from containers.implementation.utils.llm_helper import generate_json

# 🚀 Importing the prompt from your clean prompts.py file!
from containers.implementation.target_agent.prompts import TARGET_STRUCTURE_PROMPT


# ─── DATACLASSES ──────────────────────────────────────────────────────────────

@dataclass
class BuildTargetInput:
    session_id: str
    project_id: str
    f3iche: str
    company_slug: str = "unknown"


# ─── ACTIVITIES ───────────────────────────────────────────────────────────────

@activity.defn(name="build_target_structure")
async def build_target_structure(inp: BuildTargetInput) -> Dict[str, Any]:
    """
    Step 8: Generates the Target Structure (Blueprint) for ERPNext mapping.
    Uses the LLM to format doctypes and establish the import phases chronologically.
    """
    activity.logger.info("▶ build_target_structure started | session=%s f3iche=%s", inp.session_id, inp.f3iche)

    # 1. Fetch the enriched Company Profile from DB
    profile_dict = {}
    try:
        async with AsyncSessionLocal() as session:
            stmt = select(ISCompanyProfile).where(
                ISCompanyProfile.session_id == uuid.UUID(inp.session_id)
            ).order_by(ISCompanyProfile.version.desc()).limit(1)
            
            res = await session.execute(stmt)
            latest = res.scalar_one_or_none()
            
            if latest:
                profile_dict = {
                    "industry": latest.industry,
                    "required_modules": latest.required_modules,
                    "required_doctypes": latest.required_doctypes,
                    "industry_best_practices": latest.industry_best_practices,
                    "data_quality_score": latest.data_quality_score,
                    "completeness_score": latest.completeness_score
                }
    except Exception as e:
        activity.logger.error("  ❌ Failed to fetch profile from DB: %s", e)

    # ── FALLBACK: If profile has empty required_doctypes, load from f3iche template ──
    if not profile_dict.get("required_doctypes"):
        from pathlib import Path
        f3iche_path = Path(__file__).resolve().parent.parent.parent / "knowledge_base" / "common" / "f3iches" / f"{inp.f3iche}.json"
        if f3iche_path.exists():
            try:
                with open(f3iche_path, "r", encoding="utf-8") as f:
                    f3iche_data = json.load(f)
                template_doctypes = f3iche_data.get("required_doctypes", f3iche_data.get("mandatory_doctypes", []))
                template_modules = f3iche_data.get("required_modules", [])
                if template_doctypes:
                    profile_dict["required_doctypes"] = template_doctypes
                    activity.logger.info("  📋 Loaded %d required_doctypes from f3iche template '%s'",
                                         len(template_doctypes), inp.f3iche)
                if template_modules and not profile_dict.get("required_modules"):
                    profile_dict["required_modules"] = template_modules
            except Exception as e:
                activity.logger.warning("  ⚠️ Could not load f3iche template: %s", e)

    # 2. Call LLM to format the target architecture
    prompt = TARGET_STRUCTURE_PROMPT.format(
        company_profile=json.dumps(profile_dict, indent=2)
    )

    try:
        target_architecture = generate_json(prompt, temperature=0.1, max_output_tokens=2000)
        llm_enhanced = True
    except Exception as e:
        activity.logger.warning("  ⚠️ LLM Target generation failed: %s", e)
        target_architecture = {
            "required_doctypes": profile_dict.get("required_doctypes", []),
            "import_phases": {},
            "setup_steps": [],
            "llm_reasoning": "Fallback applied due to LLM error."
        }
        llm_enhanced = False

    # 3. Prepare the final result dictionary
    result = {
        "f3iche": inp.f3iche,
        "industry": profile_dict.get("industry", "Unknown"),
        "required_doctypes": target_architecture.get("required_doctypes", []),
        "import_phases": target_architecture.get("import_phases", {}),
        "setup_steps": target_architecture.get("setup_steps", []),
        "validation_rules": {}
    }

    # 4. Save the full target JSON to R2
    r2_key = f"{inp.company_slug}/{inp.project_id}/_target/target_structure.json"
    try:
        s3 = boto3.client(
            "s3",
            endpoint_url=os.getenv("R2_ENDPOINT"),
            aws_access_key_id=os.getenv("R2_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("R2_SECRET_ACCESS_KEY"),
            config=Config(signature_version="s3v4"),
            region_name="auto",
        )
        s3.put_object(
            Bucket="clean-data",
            Key=r2_key,
            Body=json.dumps(result, indent=2, default=str).encode("utf-8"),
            ContentType="application/json",
        )
        activity.logger.info("  ✅ R2 uploaded: clean-data/%s", r2_key)
    except Exception as e:
        activity.logger.error("  ❌ R2 upload failed: %s", e)

    # 5. Save to Supabase and Log Audit Trail
    target_id = uuid.uuid4()
    try:
        async with AsyncSessionLocal() as session:
            session.add(ISTargetStructure(
                id=target_id,
                session_id=uuid.UUID(inp.session_id),
                f3iche=inp.f3iche,
                llm_enhanced=llm_enhanced,
                llm_reasoning=target_architecture.get("llm_reasoning"),
                total_doctypes=len(result.get("required_doctypes", [])),
                total_setup_steps=len(result.get("setup_steps", [])),
                required_doctypes=json.dumps(result.get("required_doctypes", [])),
                setup_steps=json.dumps(result.get("setup_steps", [])),
                import_phases=json.dumps(result.get("import_phases", {})),
                r2_path=r2_key,
                created_by="system",
            ))
            await session.commit()

        from containers.implementation.file_io.persist_audit import log_audit
        await log_audit(
            session_id=inp.session_id,
            action="target_generated",
            actor="system",
            entity_type="target_structure",
            entity_id=str(target_id),
            details={"f3iche": inp.f3iche, "doctypes": len(result.get("required_doctypes", [])), "llm_enhanced": llm_enhanced},
            result="success",
        )
        activity.logger.info("  ✅ ISTargetStructure persisted.")
    except Exception as e:
        activity.logger.error("  ❌ ISTargetStructure persistence failed: %s", e)

    activity.logger.info("✅ build_target_structure done | doctypes=%d steps=%d",
                         len(result.get('required_doctypes', [])), len(result.get('setup_steps', [])))
    return result