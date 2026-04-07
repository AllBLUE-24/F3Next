"""
Profile Agent — Temporal activities for company profile build & update.

Activities persist directly to Supabase + R2. Temporal only sees "success" strings.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid

import boto3
from botocore.config import Config
from temporalio import activity

KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent.parent / "knowledge_base" / "common" / "f3iches"


def _get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=os.getenv("R2_ENDPOINT"),
        aws_access_key_id=os.getenv("R2_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("R2_SECRET_ACCESS_KEY"),
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )


def _load_file_contents_from_r2(r2_manifest_url: str) -> Dict[str, str]:
    """Download the file contents manifest from R2 and return {filename: content}."""
    if not r2_manifest_url or r2_manifest_url.startswith("error:"):
        return {}
    try:
        s3 = _get_s3_client()
        response = s3.get_object(Bucket="clean-data", Key=r2_manifest_url)
        manifest = json.loads(response["Body"].read().decode("utf-8"))
        return manifest.get("files", {})
    except Exception as e:
        activity.logger.error("  ❌ Failed to load manifest from R2: %s", e)
        return {}


# ── Embedded service logic ────────────────────────────────────────────────────

class _CompanyProfileService:
    @staticmethod
    def _load_f3iche(f3iche_id: str) -> Optional[Dict]:
        path = KNOWLEDGE_DIR / f"{f3iche_id}.json"
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    @classmethod
    def build(
        cls,
        project_id: str,
        version: int,
        f3iche: str,
        industry: str,
        action: str = "update",
        **kwargs,
    ) -> Dict[str, Any]:
        f3iche_data = cls._load_f3iche(f3iche) or {}
        
        # Load file contents from R2 manifest if URL provided
        r2_manifest_url = kwargs.get("r2_manifest_url", "")
        file_contents = _load_file_contents_from_r2(r2_manifest_url) if r2_manifest_url else {}
        
        file_summaries = []
        for fname, txt in file_contents.items():
            snippet = txt[:1500] if txt else "(empty file)"
            file_summaries.append(f"Filename: {fname}\nSample Data:\n{snippet}\n---")
            
        prompt = f"""
You are the F3Next Profile Agent. Assemble a context profile for a company named '{kwargs.get("company_name", "Unknown")}'.
Their target business niche/f3iche model is: {f3iche} (Industry: {industry}).

Based on the standard template for this niche, it includes:
Required Modules: {f3iche_data.get("required_modules", [])}

However, you must tailor this profile based on the actual DATA they uploaded:
{"".join(file_summaries)}

1. Describe their 'business_reality' based strictly on what the headers and data reveal about them.
2. List up to 3 'context_flags' if you notice issues like negative numbers, missing columns, or messy unstructured text.
3. Assign a 'data_quality_score' (High, Medium, Low).
4. Assign an 'llm_confidence' (0.0 to 1.0) indicating how confident you are that this data matches the {f3iche} business model.

Return EXACTLY this JSON structure:
{{
  "business_reality": "summary of operations",
  "context_flags": ["flag1"],
  "data_quality_score": "Medium",
  "llm_confidence": 0.85
}}
"""
        from containers.implementation.utils.llm_helper import generate_json
        
        try:
            llm_enrichment = generate_json(prompt, temperature=0.2, max_output_tokens=4000)
        except Exception as e:
            activity.logger.warning("LLM Enrichment failed: %s", e)
            llm_enrichment = {
                "business_reality": "Failed to generate context using LLM.",
                "context_flags": [],
                "data_quality_score": "Unknown",
                "llm_confidence": 0.0
            }

        return {
            "project_id": project_id,
            "version": version,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "action": action,
            "f3iche": f3iche,
            "industry": industry,
            "industry_sub":        kwargs.get("industry_sub"),
            "company_size":        kwargs.get("company_size"),
            "company_name":        kwargs.get("company_name"),
            "workflows":           [w.get("name", "") for w in f3iche_data.get("workflows", [])],
            "modules":             f3iche_data.get("required_modules", []),
            "required_doctypes":   f3iche_data.get("required_doctypes", f3iche_data.get("mandatory_doctypes", [])),
            "f3iche_user":         kwargs.get("f3iche_user"),
            "f3iche_signals":      kwargs.get("f3iche_signals"),
            "f3iche_match_status": kwargs.get("f3iche_match_status", "matched"),
            "uploaded_files":      kwargs.get("uploaded_files") or [],
            "collected_signals":   kwargs.get("collected_signals") or [],
            "target_structure":    kwargs.get("target_structure"),
            "field_mappings":      kwargs.get("field_mappings"),
            "validation_report":   kwargs.get("validation_report"),
            "import_phase":        kwargs.get("import_phase"),
            "llm_enrichment":      llm_enrichment
        }


# ── Input dataclasses ────────────────────────────────────────────────────────

@dataclass
class BuildProfileInput:
    project_id: str
    version: int
    f3iche: str
    industry: str
    session_id: str = ""
    company_slug: str = "unknown"
    action: str = "create"
    industry_sub: Optional[str] = None
    company_size: Optional[str] = None
    company_name: Optional[str] = None
    f3iche_user: Optional[str] = None
    f3iche_signals: Optional[str] = None
    f3iche_match_status: str = "matched"
    uploaded_files: List[Dict] = field(default_factory=list)
    r2_manifest_url: str = ""          # R2 manifest URL instead of raw file_contents
    collected_signals: List[str] = field(default_factory=list)
    target_structure: Optional[Dict] = None
    field_mappings: Optional[Dict] = None
    validation_report: Optional[Dict] = None
    import_phase: Optional[str] = None


@dataclass
class MergeProfileInput:
    """Merge partial update onto existing profile snapshot."""
    session_id: str
    patch: Dict[str, Any]            # only the fields that changed
    action: str = "update"


# ── Activity definitions ─────────────────────────────────────────────────────

@activity.defn(name="build_company_profile")
async def build_company_profile(inp: BuildProfileInput) -> str:
    """
    Build a fresh versioned company profile snapshot, persist to Supabase + R2.
    
    Returns: "success"
    """
    activity.logger.info("▶ build_company_profile started | project=%s f3iche=%s", inp.project_id, inp.f3iche)
    profile = _CompanyProfileService.build(
        project_id=inp.project_id,
        version=inp.version,
        f3iche=inp.f3iche,
        industry=inp.industry,
        action=inp.action,
        industry_sub=inp.industry_sub,
        company_size=inp.company_size,
        company_name=inp.company_name,
        f3iche_user=inp.f3iche_user,
        f3iche_signals=inp.f3iche_signals,
        f3iche_match_status=inp.f3iche_match_status,
        uploaded_files=inp.uploaded_files,
        r2_manifest_url=inp.r2_manifest_url,
        collected_signals=inp.collected_signals,
        target_structure=inp.target_structure,
        field_mappings=inp.field_mappings,
        validation_report=inp.validation_report,
        import_phase=inp.import_phase,
    )
    activity.logger.info("  Profile built | modules=%s", profile.get('modules', []))

    # ── Persist to Supabase (is_sessions.f3iche_profile) ─────────────────────
    if inp.session_id:
        try:
            from shared.database.db import AsyncSessionLocal
            from shared.models.is_models import ISSession
            from sqlalchemy import update

            async with AsyncSessionLocal() as session:
                await session.execute(
                    update(ISSession)
                    .where(ISSession.id == uuid.UUID(inp.session_id))
                    .values(f3iche_profile=profile)
                )
                await session.commit()
                activity.logger.info("  ✅ Supabase is_sessions.f3iche_profile updated")
        except Exception as e:
            activity.logger.error("  ❌ Supabase write failed: %s", e)

    # ── Persist to R2 ────────────────────────────────────────────────────────
    try:
        s3 = _get_s3_client()
        slug = inp.company_slug or "unknown"
        r2_key = f"{slug}/{inp.project_id}/_profile/company_context_v{inp.version}.json"
        profile_dump = {
            **profile,
            "_persisted_at": datetime.utcnow().isoformat() + "Z",
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

    activity.logger.info("✅ build_company_profile done")
    return "success"


@activity.defn(name="merge_company_profile")
async def merge_company_profile(inp: MergeProfileInput) -> str:
    """
    Read current profile from Supabase, merge patch, persist back.
    
    Returns: "success"
    """
    activity.logger.info("▶ merge_company_profile started | session=%s action=%s patch_keys=%s",
                         inp.session_id, inp.action, list(inp.patch.keys()))

    from shared.database.db import AsyncSessionLocal
    from shared.models.is_models import ISSession
    from sqlalchemy import select, update

    async with AsyncSessionLocal() as session:
        # Read current profile from Supabase
        stmt = select(ISSession).where(ISSession.id == uuid.UUID(inp.session_id))
        result = await session.execute(stmt)
        is_session = result.scalar_one_or_none()

        if not is_session:
            activity.logger.error("  ❌ Session %s not found", inp.session_id)
            return "error:session_not_found"

        existing = is_session.f3iche_profile or {}
        new_version = existing.get("version", 0) + 1

        # Merge: patch values override existing
        merged = {**existing, **{k: v for k, v in inp.patch.items() if v is not None}}
        merged["version"] = new_version
        merged["action"] = inp.action
        merged["timestamp"] = datetime.utcnow().isoformat() + "Z"

        # Write back to Supabase
        await session.execute(
            update(ISSession)
            .where(ISSession.id == uuid.UUID(inp.session_id))
            .values(f3iche_profile=merged)
        )
        await session.commit()
        activity.logger.info("  ✅ Profile merged and persisted | version=%d", new_version)

    activity.logger.info("✅ merge_company_profile done")
    return "success"