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
    discovery_alignment_score: Optional[float] = None


@dataclass
class MergeProfileInput:
    """Merge partial update onto existing profile snapshot."""
    session_id: str
    patch: Dict[str, Any]            # only the fields that changed
    action: str = "update"

@dataclass
class AlignDiscoverySignalsInput:
    session_id: str
    project_id: str

@dataclass
class RetrieveIndustryKnowledgeInput:
    session_id: str
    industry: str
    company_size: Optional[str] = None
    differentiators: str = ""

@dataclass
class EnrichCompanyProfileInput:
    session_id: str
    project_id: str
    company_slug: str
    r2_manifest_url: str

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

    # ── Persist to Supabase (is_company_profiles — v2 schema) ────────────────
    profile_id = None
    if inp.session_id:
        try:
            from shared.database.db import AsyncSessionLocal
            from shared.models.is_models import ISCompanyProfile

            slug = inp.company_slug or "unknown"
            r2_key = f"{slug}/{inp.project_id}/_profile/company_context_v{inp.version}.json"
            profile_id = uuid.uuid4()

            llm_enrichment = profile.get("llm_enrichment", {})

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
                    discovery_alignment_score=inp.discovery_alignment_score,
                    workflows=profile.get("workflows"),
                    required_modules=profile.get("modules"),
                    required_doctypes=profile.get("required_doctypes"),
                    business_reality=llm_enrichment.get("business_reality"),
                    context_flags=llm_enrichment.get("context_flags"),
                    data_quality_score=_parse_dqs(llm_enrichment.get("data_quality_score")),
                    llm_confidence=llm_enrichment.get("llm_confidence"),
                    r2_path=r2_key,
                    created_by="system",
                ))
                await session.commit()
                activity.logger.info("  ✅ Supabase is_company_profiles inserted (v%d)", inp.version)
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

    # ── Audit trail ──────────────────────────────────────────────────────────
    if inp.session_id:
        from containers.implementation.file_io.persist_audit import log_audit
        await log_audit(
            session_id=inp.session_id,
            action="profile_built",
            actor="system",
            entity_type="profile",
            entity_id=str(profile_id) if profile_id else None,
            details={"version": inp.version, "f3iche": inp.f3iche},
            result="success",
        )

    activity.logger.info("✅ build_company_profile done")
    return "success"


def _parse_dqs(val) -> Optional[float]:
    """Convert data_quality_score to float (LLM may return 'High'/'Medium'/'Low')."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    mapping = {"high": 0.9, "medium": 0.6, "low": 0.3}
    return mapping.get(str(val).lower(), 0.5)


@activity.defn(name="merge_company_profile")
async def merge_company_profile(inp: MergeProfileInput) -> str:
    """
    Read latest profile from is_company_profiles, create new version with merged patch.
    
    Returns: "success"
    """
    activity.logger.info("▶ merge_company_profile started | session=%s action=%s patch_keys=%s",
                         inp.session_id, inp.action, list(inp.patch.keys()))

    from shared.database.db import AsyncSessionLocal
    from shared.models.is_models import ISCompanyProfile
    from sqlalchemy import select

    async with AsyncSessionLocal() as session:
        # Read latest profile version
        stmt = (
            select(ISCompanyProfile)
            .where(ISCompanyProfile.session_id == uuid.UUID(inp.session_id))
            .order_by(ISCompanyProfile.version.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        latest = result.scalar_one_or_none()

        if not latest:
            activity.logger.error("  ❌ No profile found for session %s", inp.session_id)
            return "error:profile_not_found"

        new_version = latest.version + 1

        # Create new version with merged values
        new_profile = ISCompanyProfile(
            id=uuid.uuid4(),
            session_id=uuid.UUID(inp.session_id),
            version=new_version,
            f3iche=inp.patch.get("f3iche", latest.f3iche),
            industry=inp.patch.get("industry", latest.industry),
            industry_sub=inp.patch.get("industry_sub", latest.industry_sub),
            company_name=inp.patch.get("company_name", latest.company_name),
            company_size=inp.patch.get("company_size", latest.company_size),
            workflows=inp.patch.get("workflows", latest.workflows),
            required_modules=inp.patch.get("required_modules", latest.required_modules),
            required_doctypes=inp.patch.get("required_doctypes", latest.required_doctypes),
            business_reality=inp.patch.get("business_reality", latest.business_reality),
            context_flags=inp.patch.get("context_flags", latest.context_flags),
            data_quality_score=inp.patch.get("data_quality_score", latest.data_quality_score),
            llm_confidence=inp.patch.get("llm_confidence", latest.llm_confidence),
            r2_path=latest.r2_path,
            created_by="user",
        )
        session.add(new_profile)
        await session.commit()
        activity.logger.info("  ✅ Profile merged and persisted | version=%d", new_version)

    # Audit trail
    from containers.implementation.file_io.persist_audit import log_audit
    await log_audit(
        session_id=inp.session_id,
        action="profile_merged",
        actor="user",
        entity_type="profile",
        details={"version": new_version, "patch_keys": list(inp.patch.keys())},
        result="success",
    )

    activity.logger.info("✅ merge_company_profile done")
    return "success"

@activity.defn(name="align_discovery_and_signals")
async def align_discovery_and_signals(inp: AlignDiscoverySignalsInput) -> Dict[str, Any]:
    """
    Step 6a: Compare Discovery data (from hooks) with Signals data (from is_f3iche_scores)
    using an LLM to generate an alignment score and identify mismatches.
    """
    activity.logger.info("▶ align_discovery_and_signals started | session=%s", inp.session_id)

    from shared.database.db import AsyncSessionLocal
    from shared.models.is_models import ISSession, ISF3icheScore
    from sqlalchemy import select, update, text
    from containers.implementation.utils.llm_helper import generate_json
    from containers.implementation.profile_agent.prompts import ALIGNMENT_PROMPT

    discovery_data = {}
    signals_data = []

    async with AsyncSessionLocal() as session:
        # 1. Fetch Discovery Data (Safely querying the 'hooks' table directly)
        stmt_hooks = text("SELECT discovery_metadata FROM hooks WHERE project_id = :pid ORDER BY created_at DESC LIMIT 1")
        res_hooks = await session.execute(stmt_hooks, {"pid": inp.project_id})
        hook_row = res_hooks.fetchone()
        if hook_row and hook_row[0]:
            discovery_data = hook_row[0]

        # 2. Fetch Signals Data
        stmt_signals = select(ISF3icheScore).where(
            ISF3icheScore.session_id == uuid.UUID(inp.session_id),
            ISF3icheScore.source == "signals"
        )
        res_signals = await session.execute(stmt_signals)
        for score_row in res_signals.scalars():
            signals_data.append({
                "f3iche": score_row.f3iche,
                "confidence": score_row.confidence,
                "score": score_row.score
            })

    # 3. Call the LLM
    prompt = ALIGNMENT_PROMPT.format(
        discovery_data=json.dumps(discovery_data, indent=2),
        signals_data=json.dumps(signals_data, indent=2)
    )

    try:
        alignment_result = generate_json(prompt, temperature=0.1, max_output_tokens=1000)
    except Exception as e:
        activity.logger.warning("  ⚠️ LLM Alignment failed: %s", e)
        alignment_result = {
            "alignment_score": 0.5,
            "mismatches": [f"LLM parsing error: {e}"],
            "recommended_f3iche": signals_data[0]["f3iche"] if signals_data else "unknown",
            "reasoning": "Fallback applied due to LLM error."
        }

    # 4. Update Supabase & Write Audit Log
    try:
        async with AsyncSessionLocal() as session:
            # Safely extract variables (they might be missing if discovery was skipped)
            f3iche = discovery_data.get("f3iche") if isinstance(discovery_data, dict) else None
            industry = discovery_data.get("industry") if isinstance(discovery_data, dict) else None
            company_size = discovery_data.get("company_size") if isinstance(discovery_data, dict) else None

            update_vals = {}
            if f3iche: update_vals["discovery_f3iche"] = f3iche
            if industry: update_vals["discovery_industry"] = industry
            if company_size: update_vals["discovery_company_size"] = company_size

            # Update is_sessions table if we have discovery data
            if update_vals:
                await session.execute(
                    update(ISSession)
                    .where(ISSession.id == uuid.UUID(inp.session_id))
                    .values(**update_vals)
                )
                await session.commit()
                activity.logger.info("  ✅ Updated is_sessions with discovery metadata.")
            else:
                activity.logger.info("  ⚠️ No valid discovery metadata found to update is_sessions.")

        # Write the Audit Trail
        from containers.implementation.file_io.persist_audit import log_audit
        await log_audit(
            session_id=inp.session_id,
            action="discovery_signals_aligned",
            actor="llm",
            details={
                "alignment_score": alignment_result.get("alignment_score"),
                "mismatches": alignment_result.get("mismatches")
            },
            result="success"
        )
        activity.logger.info("  ✅ Audit log written for discovery_signals_aligned.")

    except Exception as e:
        activity.logger.error("  ❌ Database update failed during alignment: %s", e)

    activity.logger.info("✅ align_discovery_and_signals done | score=%s", alignment_result.get("alignment_score"))
    return alignment_result


# -----------------------------------------------------------------------------
# STEP 7a: RAG-Based Industry Knowledge Retrieval
# -----------------------------------------------------------------------------
@activity.defn(name="retrieve_industry_knowledge")
async def retrieve_industry_knowledge(inp: RetrieveIndustryKnowledgeInput) -> Dict[str, Any]:
    activity.logger.info("▶ retrieve_industry_knowledge (RAG) started | industry=%s", inp.industry)

    from shared.database.db import AsyncSessionLocal
    from shared.models.is_models import ISCompanyProfile
    from sqlalchemy import update, select, text
    from containers.implementation.utils.llm_helper import generate_json
    from langchain_google_genai import GoogleGenerativeAIEmbeddings
    import uuid

    # 1. Build the search query
    # 1. Build the search query
    search_query = f"Industry: {inp.industry}. Size: {inp.company_size}. Unique aspects: {inp.differentiators}. What compliance requirements, best practices, and workflows are typical?"
    
    # 2. Generate Vector Embedding using the new REST API
    try:
        import requests
        from llm_router import key_pool
        
        # Get a key from your router
        current_key = next(key_pool)
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-001:embedContent?key={current_key}"
        payload = {
            "model": "models/gemini-embedding-001",
            "content": {"parts": [{"text": search_query}]}
        }
        response = requests.post(url, headers={'Content-Type': 'application/json'}, json=payload)
        response_data = response.json()
        
        if "error" in response_data:
            raise Exception(response_data["error"])
            
        vector = response_data['embedding']['values']
        vector_str = "[" + ",".join(map(str, vector)) + "]"
        
    except Exception as e:
        activity.logger.error("  ❌ Failed to generate embedding: %s", e)
        vector_str = None

    # 3. Vector Similarity Search in Supabase
    retrieved_docs = []
    if vector_str:
        try:
            async with AsyncSessionLocal() as session:
                # We use raw SQL with `<=>` which calculates cosine distance
                # We use raw SQL with `<=>` which calculates cosine distance
                stmt = text("""
                    SELECT content 
                    FROM kb_embeddings 
                    ORDER BY embedding <=> CAST(:vector AS vector)
                    LIMIT 5
                """)

                res = await session.execute(stmt, {"vector": vector_str})
                
                for row in res:
                    retrieved_docs.append(row[0])
                    
            activity.logger.info("  ✅ Retrieved %d relevant chunks from pgvector", len(retrieved_docs))
        except Exception as e:
            activity.logger.error("  ❌ Vector search failed: %s", e)

    # Fallback if no docs found
    if not retrieved_docs:
        retrieved_docs.append("No specific industry knowledge found in database. Rely on general ERP principles.")

    # 4. Call LLM to synthesize the RAG results
    context_str = "\n\n---\n\n".join(retrieved_docs)
    prompt = f"""
You are the F3Next Industry Expert AI. 

Based strictly on these retrieved industry knowledge snippets:
{context_str}

Summarize the operational realities for a company in: {inp.industry} (Size: {inp.company_size}).
1. Key compliance requirements
2. Best practices
3. Typical workflows
4. Common challenges

Return EXACTLY this JSON structure:
{{
  "industry_differentiators": [
    "List 3-4 unique operational requirements based on the snippets"
  ],
  "industry_best_practices": {{
    "compliance": ["List compliance standards"],
    "workflows": ["List crucial ERP workflows"],
    "challenges": ["List common challenges"]
  }}
}}
"""

    try:
        industry_insights = generate_json(prompt, temperature=0.2, max_output_tokens=1500)
    except Exception as e:
        activity.logger.warning("  ⚠️ LLM Synthesis failed: %s", e)
        industry_insights = {"industry_differentiators": [], "industry_best_practices": {}}

    # 5. Update Supabase is_company_profiles
    try:
        async with AsyncSessionLocal() as session:
            stmt = (
                select(ISCompanyProfile)
                .where(ISCompanyProfile.session_id == uuid.UUID(inp.session_id))
                .order_by(ISCompanyProfile.version.desc())
                .limit(1)
            )
            res = await session.execute(stmt)
            latest_profile = res.scalar_one_or_none()

            if latest_profile:
                await session.execute(
                    update(ISCompanyProfile)
                    .where(ISCompanyProfile.id == latest_profile.id)
                    .values(
                        industry_differentiators=industry_insights.get("industry_differentiators", []),
                        industry_best_practices=industry_insights.get("industry_best_practices", {})
                    )
                )
                await session.commit()
    except Exception as e:
        activity.logger.error("  ❌ Database update failed: %s", e)

    activity.logger.info("✅ retrieve_industry_knowledge done")
    return industry_insights


# -----------------------------------------------------------------------------
# STEP 7b: Enrich Company Profile
# -----------------------------------------------------------------------------
@activity.defn(name="enrich_company_profile")
async def enrich_company_profile(inp: EnrichCompanyProfileInput) -> Dict[str, Any]:
    """
    Step 7b: Enrich the company profile with data observations and scores,
    then save the final version to DB and R2.
    """
    activity.logger.info("▶ enrich_company_profile started | session=%s", inp.session_id)

    from shared.database.db import AsyncSessionLocal
    from shared.models.is_models import ISCompanyProfile
    from sqlalchemy import update, select
    from containers.implementation.utils.llm_helper import generate_json
    from containers.implementation.profile_agent.prompts import PROFILE_ENRICHMENT_PROMPT
    import boto3
    from botocore.config import Config

    def get_s3_client():
        return boto3.client(
            "s3",
            endpoint_url=os.getenv("R2_ENDPOINT"),
            aws_access_key_id=os.getenv("R2_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("R2_SECRET_ACCESS_KEY"),
            config=Config(signature_version="s3v4"),
            region_name="auto",
        )

    # 1. Fetch current profile from DB
    profile_dict = {}
    profile_id = None
    profile_version = 1
    
    try:
        async with AsyncSessionLocal() as session:
            stmt = select(ISCompanyProfile).where(
                ISCompanyProfile.session_id == uuid.UUID(inp.session_id)
            ).order_by(ISCompanyProfile.version.desc()).limit(1)
            
            res = await session.execute(stmt)
            latest = res.scalar_one_or_none()
            
            if latest:
                profile_id = latest.id
                profile_version = latest.version
                profile_dict = {
                    "f3iche": latest.f3iche,
                    "industry": latest.industry,
                    "required_modules": latest.required_modules,
                    "required_doctypes": latest.required_doctypes,
                    "industry_best_practices": latest.industry_best_practices
                }
    except Exception as e:
        activity.logger.error("  ❌ Failed to fetch profile: %s", e)
        return {"status": "error"}

    # 2. Fetch Manifest / File Snippets from R2
    file_contents = {}
    if inp.r2_manifest_url:
        try:
            s3 = get_s3_client()
            response = s3.get_object(Bucket="clean-data", Key=inp.r2_manifest_url)
            manifest = json.loads(response["Body"].read().decode("utf-8"))
            file_contents = manifest.get("files", {})
        except Exception as e:
            activity.logger.error("  ❌ Failed to load manifest: %s", e)

    snippets = []
    for fname, txt in file_contents.items():
        snippets.append(f"File: {fname}\nData: {str(txt)[:1000]}\n---")

    # 3. Call LLM for Enrichment
    prompt = PROFILE_ENRICHMENT_PROMPT.format(
        current_profile=json.dumps(profile_dict, indent=2),
        data_snippets="\n".join(snippets)
    )

    try:
        enrichment_data = generate_json(prompt, temperature=0.2, max_output_tokens=1500)
    except Exception as e1:
        activity.logger.warning("  ⚠️ LLM Enrichment attempt 1 failed: %s — retrying...", e1)
        import time
        time.sleep(2)
        try:
            enrichment_data = generate_json(prompt, temperature=0.3, max_output_tokens=1500)
        except Exception as e2:
            activity.logger.warning("  ⚠️ LLM Enrichment attempt 2 failed: %s — using f3iche template fallback", e2)
            enrichment_data = {
                "data_quality_score": 0.5,
                "completeness_score": 0.5,
                "data_observations": ["LLM enrichment failed after 2 attempts — using template defaults"],
                "recommended_customizations": []
            }
            # ── FALLBACK: populate required_modules/doctypes from f3iche template ──
            if profile_dict.get("f3iche"):
                from pathlib import Path
                f3iche_path = Path(__file__).resolve().parent.parent.parent / "knowledge_base" / "common" / "f3iches" / f"{profile_dict['f3iche']}.json"
                if f3iche_path.exists():
                    try:
                        with open(f3iche_path, "r", encoding="utf-8") as f:
                            f3iche_data = json.load(f)
                        if not profile_dict.get("required_modules"):
                            profile_dict["required_modules"] = f3iche_data.get("required_modules", [])
                        if not profile_dict.get("required_doctypes"):
                            profile_dict["required_doctypes"] = f3iche_data.get("required_doctypes", 
                                f3iche_data.get("mandatory_doctypes", []))
                        activity.logger.info("  📋 Loaded f3iche template defaults for %s", profile_dict["f3iche"])
                    except Exception:
                        pass

    # 4. Save Final JSON to R2
    r2_key = f"{inp.company_slug}/{inp.project_id}/_profile/company_context_v{profile_version}.json"
    
    # Merge existing profile with new enrichment data
    final_profile = {
        **profile_dict,
        "version": profile_version,
        "session_id": inp.session_id,
        "data_quality_score": enrichment_data.get("data_quality_score"),
        "completeness_score": enrichment_data.get("completeness_score"),
        "data_observations": enrichment_data.get("data_observations", []),
        "recommended_customizations": enrichment_data.get("recommended_customizations", []),
        "_persisted_at": datetime.utcnow().isoformat() + "Z"
    }

    try:
        s3 = get_s3_client()
        s3.put_object(
            Bucket="clean-data",
            Key=r2_key,
            Body=json.dumps(final_profile, indent=2).encode("utf-8"),
            ContentType="application/json"
        )
    except Exception as e:
        activity.logger.error("  ❌ Failed to save final profile to R2: %s", e)

    # 5. Update DB and Write Audit Log
    if profile_id:
        try:
            async with AsyncSessionLocal() as session:
                await session.execute(
                    update(ISCompanyProfile)
                    .where(ISCompanyProfile.id == profile_id)
                    .values(
                        data_quality_score=enrichment_data.get("data_quality_score"),
                        completeness_score=enrichment_data.get("completeness_score"),
                        r2_path=r2_key
                    )
                )
                await session.commit()
                
            from containers.implementation.file_io.persist_audit import log_audit
            await log_audit(
                session_id=inp.session_id,
                action="profile_built",
                actor="llm",
                details={"version": profile_version, "quality_score": enrichment_data.get("data_quality_score")},
                result="success"
            )
        except Exception as e:
            activity.logger.error("  ❌ DB update failed: %s", e)

    activity.logger.info("✅ enrich_company_profile done")
    return enrichment_data