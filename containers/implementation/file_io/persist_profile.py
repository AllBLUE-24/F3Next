"""
File IO — persist_profile activity.

Saves the company profile to both:
  1. Supabase → is_company_profiles (versioned rows)
  2. R2       → clean-data/{company_slug}/{project_id}/_profile/company_context_v{N}.json

Returns: "success" (tiny string for Temporal event history)
"""
from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import boto3
from botocore.config import Config
from temporalio import activity


def _get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=os.getenv("R2_ENDPOINT"),
        aws_access_key_id=os.getenv("R2_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("R2_SECRET_ACCESS_KEY"),
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )


@dataclass
class PersistProfileInput:
    session_id: str
    project_id: str
    company_slug: str
    version: int = 1
    # Profile fields
    f3iche: str = ""
    industry: Optional[str] = None
    industry_sub: Optional[str] = None
    company_name: Optional[str] = None
    company_size: Optional[str] = None
    # F3iche-derived config
    workflows: Optional[List] = None
    required_modules: Optional[List] = None
    required_doctypes: Optional[List] = None
    # LLM enrichment
    business_reality: Optional[str] = None
    context_flags: Optional[List] = None
    data_quality_score: Optional[float] = None
    llm_confidence: Optional[float] = None
    # Discovery comparison
    discovery_alignment_score: Optional[float] = None
    discovery_mismatches: Optional[Dict] = None
    # Full profile dict for R2
    full_profile: Optional[Dict[str, Any]] = None
    created_by: str = "system"


@activity.defn(name="persist_profile")
async def persist_profile(inp: PersistProfileInput) -> str:
    """
    Insert a versioned row into is_company_profiles + upload to R2.

    Returns: "success"
    """
    activity.logger.info("▶ persist_profile started | session=%s slug=%s version=%d",
                         inp.session_id, inp.company_slug, inp.version)

    profile_id = uuid.uuid4()

    # ── 1. Supabase (is_company_profiles) ────────────────────────────────────
    try:
        from shared.database.db import AsyncSessionLocal
        from shared.models.is_models import ISCompanyProfile

        slug = inp.company_slug or "unknown"
        r2_key = f"{slug}/{inp.project_id}/_profile/company_context_v{inp.version}.json"

        async with AsyncSessionLocal() as session:
            session.add(ISCompanyProfile(
                id=profile_id,
                session_id=uuid.UUID(inp.session_id),
                version=inp.version,
                f3iche=inp.f3iche,
                industry=inp.industry,
                industry_sub=inp.industry_sub,
                company_name=inp.company_name,
                company_size=inp.company_size,
                workflows=inp.workflows,
                required_modules=inp.required_modules,
                required_doctypes=inp.required_doctypes,
                business_reality=inp.business_reality,
                context_flags=inp.context_flags,
                data_quality_score=inp.data_quality_score,
                llm_confidence=inp.llm_confidence,
                discovery_alignment_score=inp.discovery_alignment_score,
                discovery_mismatches=inp.discovery_mismatches,
                r2_path=r2_key,
                created_by=inp.created_by,
            ))
            await session.commit()
            activity.logger.info("  ✅ Supabase is_company_profiles inserted (v%d)", inp.version)

    except Exception as e:
        activity.logger.error("  ❌ Supabase write failed: %s", e)

    # ── 2. R2 (versioned JSON backup) ────────────────────────────────────────
    try:
        s3 = _get_s3_client()
        profile_dump = inp.full_profile or {
            "f3iche": inp.f3iche,
            "industry": inp.industry,
            "industry_sub": inp.industry_sub,
            "company_name": inp.company_name,
            "company_size": inp.company_size,
            "workflows": inp.workflows,
            "required_modules": inp.required_modules,
            "required_doctypes": inp.required_doctypes,
            "business_reality": inp.business_reality,
            "context_flags": inp.context_flags,
            "data_quality_score": inp.data_quality_score,
            "llm_confidence": inp.llm_confidence,
        }
        profile_dump["_persisted_at"] = datetime.utcnow().isoformat() + "Z"
        profile_dump["_version"] = inp.version

        s3.put_object(
            Bucket="clean-data",
            Key=r2_key,
            Body=json.dumps(profile_dump, indent=2, default=str).encode("utf-8"),
            ContentType="application/json",
        )
        activity.logger.info("  ✅ R2 uploaded: clean-data/%s", r2_key)

    except Exception as e:
        activity.logger.error("  ❌ R2 write failed: %s", e)

    # ── 3. Audit trail ───────────────────────────────────────────────────────
    from containers.implementation.file_io.persist_audit import log_audit
    await log_audit(
        session_id=inp.session_id,
        action="profile_built",
        actor=inp.created_by,
        entity_type="profile",
        entity_id=str(profile_id),
        details={"version": inp.version, "f3iche": inp.f3iche},
        result="success",
    )

    activity.logger.info("✅ persist_profile done")
    return "success"
