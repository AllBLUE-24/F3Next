"""
File IO — persist_profile activity.

Saves the company profile to both:
  1. Supabase → is_sessions.f3iche_profile (JSONB column)
  2. R2       → clean-data/{company_slug}/{project_id}/_profile/company_context_v{N}.json

Returns: "success" (tiny string for Temporal event history)
"""
from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

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
    project_id: str
    company_slug: str
    profile: Dict[str, Any]
    version: int = 1
    session_id: Optional[str] = None


@activity.defn(name="persist_profile")
async def persist_profile(inp: PersistProfileInput) -> str:
    """
    Dual-write company profile to Supabase (is_sessions) and R2.

    Returns: "success"
    """
    activity.logger.info("▶ persist_profile started | project=%s slug=%s version=%d",
                         inp.project_id, inp.company_slug, inp.version)

    # ── 1. Supabase (is_sessions.f3iche_profile) ─────────────────────────────
    try:
        from shared.database.db import AsyncSessionLocal
        from shared.models.is_models import ISSession
        from sqlalchemy import update

        if inp.session_id:
            async with AsyncSessionLocal() as session:
                await session.execute(
                    update(ISSession)
                    .where(ISSession.id == uuid.UUID(inp.session_id))
                    .values(f3iche_profile=inp.profile)
                )
                await session.commit()
                activity.logger.info("  ✅ Supabase is_sessions.f3iche_profile updated (v%d)", inp.version)
        else:
            activity.logger.warning("  ⚠️ No session_id provided, skipping Supabase write")

    except Exception as e:
        activity.logger.error("  ❌ Supabase write failed: %s", e)

    # ── 2. R2 (versioned JSON backup) ────────────────────────────────────────
    try:
        s3 = _get_s3_client()

        slug = inp.company_slug or "unknown"
        r2_key = f"{slug}/{inp.project_id}/_profile/company_context_v{inp.version}.json"

        # Add metadata to the profile dump
        profile_dump = {
            **inp.profile,
            "_persisted_at": datetime.utcnow().isoformat() + "Z",
            "_version": inp.version,
        }

        s3.put_object(
            Bucket="clean-data",
            Key=r2_key,
            Body=json.dumps(profile_dump, indent=2, default=str).encode("utf-8"),
            ContentType="application/json",
        )
        activity.logger.info("  ✅ R2 uploaded: clean-data/%s", r2_key)

    except Exception as e:
        activity.logger.error("  ❌ R2 write failed: %s", e)

    activity.logger.info("✅ persist_profile done")
    return "success"
