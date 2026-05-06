"""
Signals Agent — Temporal activities for F3iche inference and verification.
Rewritten to match the new weighted signals_registry.json schema (rules-based).

Reads file contents from R2 manifest URL instead of receiving raw content.
Returns small dicts — already safe for Temporal event history.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import boto3
from botocore.config import Config
from temporalio import activity

KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent.parent / "knowledge_base" / "common"


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


class _SignalsInferenceService:
    def __init__(self):
        self._registry_summary: Optional[Dict] = None

    def _load_registry_summary(self) -> Dict:
        if self._registry_summary is None:
            path = KNOWLEDGE_DIR / "signals_registry.json"
            activity.logger.info("▶ Loading signals registry from %s", path)
            with open(path, "r", encoding="utf-8") as f:
                registry = json.load(f)
            
            self._registry_summary = {
                "niche_ids": registry.get("_meta", {}).get("niche_ids", []),
                "niche_definitions": registry.get("niche_score_to_id_map", {})
            }
        return self._registry_summary

    def infer_f3iche(
        self,
        uploaded_files: List[Dict],
        file_contents: Optional[Dict[str, str]] = None,
    ) -> tuple[str, float, List[str]]:
        from containers.implementation.utils.llm_helper import generate_json
        
        registry_summary = self._load_registry_summary()
        niche_ids = registry_summary.get("niche_ids", [])
        
        filenames = [f.get("file_name", f.get("name", "")) for f in uploaded_files]
        
        file_summaries = []
        if file_contents:
            for fname, text in file_contents.items():
                snippet = text[:1500] if text else "(empty file)"
                file_summaries.append(f"Filename: {fname}\nContent Snippet:\n{snippet}\n---")
        else:
            for fname in filenames:
                file_summaries.append(f"Filename: {fname}\n---")
                
        prompt = f"""
You are the F3Next Signals Agent. Your job is to infer the core business type (F3iche) of a company based on the files they have uploaded to our ERP generation system.

You have the following possible niches:
{json.dumps(registry_summary, indent=2)}

Uploaded Files:
{json.dumps(filenames)}

Sample Data Extracted from Files:
{"".join(file_summaries)}

Analyze the filenames and content (specifically looking at column headers, data tracking structures, and terminology).
1. Choose the SINGLE BEST MATCHING NICHE from the `niche_ids` list. Do NOT invent a new ID.
2. Provide a confidence score between 0.0 and 1.0.
3. List 3-5 distinct, compelling signals you found that led to this conclusion (short phrases, e.g. "Contains drawing/blueprint numbers", "No BOM structures present").

Return ONLY a valid JSON object matching this schema exactly:
{{
  "f3iche": "the_niche_id",
  "confidence": 0.85,
  "collected_signals": ["signal 1", "signal 2", "signal 3"]
}}
"""
        try:
            result = generate_json(prompt, temperature=0.1, max_output_tokens=4000)
            inferred_f3iche = result.get("f3iche", "trading")
            
            if inferred_f3iche not in niche_ids:
                inferred_f3iche = "trading"
                
            confidence = float(result.get("confidence", 0.0))
            signals = result.get("collected_signals", [])
            
            return (inferred_f3iche, confidence, signals)
        except Exception as e:
            activity.logger.error("LLM Inference failed: %s", e)
            return ("trading", 0.0, [f"Failed to infer via LLM: {str(e)}"])


class _F3icheVerificationService:
    # ── PROTOCOL-COMPLIANT: No hardcoded F3iche ID lists. ─────────────────────
    # Broad category is derived from the F3iche ID prefix (e.g.
    # "manufacturing_project_chemical" → "manufacturing").
    # Adding new F3iches to signals_registry.json requires zero changes here.
    # ──────────────────────────────────────────────────────────────────────────

    # Kept only for generic user-facing aliases ("trade", "service", etc.)
    # that do NOT follow the niche ID naming convention.
    _GENERIC_ALIASES: Dict[str, str] = {
        "trade":         "trading",
        "distributor":   "trading",
        "trader":        "trading",
        "manufacture":   "manufacturing",
        "production":    "manufacturing",
        "maker":         "manufacturing",
        "services":      "service",
        "consulting":    "service",
    }

    @classmethod
    def _get_broad_category(cls, f3iche: str) -> str:
        """Derive broad category from F3iche ID without any hardcoded lists.

        Strategy:
        1. If the value is already a broad category prefix, return it.
        2. If the value follows the niche ID convention (e.g. 'trading_fmcg_distributor'),
           extract and return the prefix ('trading').
        3. Check generic user-facing aliases (e.g. 'trade' → 'trading').
        4. Return the value as-is so comparisons still work.
        """
        if not f3iche:
            return ""
        f = f3iche.lower().strip()
        # Broad category prefix match: trading_*, manufacturing_*, service_*
        for prefix in ("trading", "manufacturing", "service"):
            if f == prefix or f.startswith(f"{prefix}_"):
                return prefix
        # Generic alias fallback (for human-entered values from discovery)
        return cls._GENERIC_ALIASES.get(f, f)

    @classmethod
    def verify(cls, f3iche_user: str, f3iche_signals: str, confidence: float = 0.0) -> tuple[bool, str, Optional[str]]:
        u_cat = cls._get_broad_category(f3iche_user)
        s_cat = cls._get_broad_category(f3iche_signals)

        if not u_cat:
            return (False, "pending_clarification", "Please confirm your business type from the discovery chat.")
        if not s_cat:
            return (True, "matched", None)
        if u_cat == s_cat:
            return (True, "matched", None)
        msg = (
            f"Our analysis suggests you might be a **{s_cat}** business, "
            f"but you indicated **{u_cat}**. Could you clarify which best describes your operations?"
        )
        return (False, "mismatch", msg)


# ── Input dataclasses ────────────────────────────────────────────────────────

@dataclass
class InferF3icheInput:
    uploaded_files: List[Dict]
    r2_manifest_url: str = ""         # R2 key to file contents manifest
    session_id: str = ""              # v2: needed for DB persistence


@dataclass
class VerifyF3icheInput:
    f3iche_user: str
    f3iche_signals: str
    confidence: float = 0.0
    session_id: str = ""              # v2: needed for DB persistence


# ── Activity definitions ─────────────────────────────────────────────────────

@activity.defn(name="infer_f3iche")
async def infer_f3iche(inp: InferF3icheInput) -> Dict:
    """Infer F3iche from uploaded file names and content signals.
    
    Downloads file contents from R2 manifest URL instead of receiving them directly.
    Returns a small dict — already safe for Temporal event history.
    Persists ISFileSignal + ISF3icheScore rows to DB.
    """
    activity.logger.info("▶ infer_f3iche started | files=%d manifest=%s",
                         len(inp.uploaded_files), inp.r2_manifest_url)
    
    # Load file contents from R2 manifest
    file_contents = _load_file_contents_from_r2(inp.r2_manifest_url)
    activity.logger.info("  Loaded %d file contents from R2 manifest", len(file_contents))
    
    svc = _SignalsInferenceService()
    f3iche_id, confidence, signals = svc.infer_f3iche(inp.uploaded_files, file_contents)
    result = {
        "f3iche": f3iche_id,
        "confidence": round(confidence, 2),
        "collected_signals": signals,
    }

    # ── Persist to DB (v2 schema) ────────────────────────────────────────────
    if inp.session_id:
        try:
            import uuid
            from shared.database.db import AsyncSessionLocal
            from shared.models.is_models import ISFileSignal, ISF3icheScore

            async with AsyncSessionLocal() as session:
                # Write ISFileSignal rows — one per collected signal
                for sig_text in signals:
                    session.add(ISFileSignal(
                        id=uuid.uuid4(),
                        session_id=uuid.UUID(inp.session_id),
                        signal_type="data_pattern",
                        pattern_matched=sig_text,
                        suggests_f3iche=f3iche_id,
                        weight=1.0,
                        confidence=confidence,
                    ))

                # Write ISF3icheScore row for the inferred niche
                session.add(ISF3icheScore(
                    id=uuid.uuid4(),
                    session_id=uuid.UUID(inp.session_id),
                    f3iche=f3iche_id,
                    score=confidence,
                    confidence=confidence,
                    source="signals",
                    is_selected=True,
                ))

                await session.commit()
                activity.logger.info("  ✅ Persisted %d ISFileSignal + 1 ISF3icheScore rows", len(signals))

            # Audit trail
            from containers.implementation.file_io.persist_audit import log_audit
     # 1. Audit trail for Signal Detection (Blueprint Step 4)
            await log_audit(
                session_id=inp.session_id,
                action="signals_detected",
                actor="llm",
                details={"total_signals": len(signals), "files_scanned": len(inp.uploaded_files)},
                result="success",
            )

            # 2. Audit trail for F3iche Inference (Blueprint Step 5)
            await log_audit(
                session_id=inp.session_id,
                action="f3iche_inferred",
                actor="system",
                details={"f3iche": f3iche_id, "confidence": confidence, "signal_count": len(signals)},
                result="success",
            )

        except Exception as e:
            activity.logger.error("  ❌ DB persistence failed: %s", e)

    activity.logger.info("✅ infer_f3iche done | inferred: %s (%.0f%%) via %d signals",
                         f3iche_id, confidence*100, len(signals))
    return result


@activity.defn(name="verify_f3iche")
async def verify_f3iche(inp: VerifyF3icheInput) -> Dict:
    """Verify user-stated F3iche against signals-inferred F3iche."""
    activity.logger.info("▶ verify_f3iche started | user=%s signals=%s", inp.f3iche_user, inp.f3iche_signals)
    
    svc = _F3icheVerificationService()
    is_match, status, msg = svc.verify(inp.f3iche_user, inp.f3iche_signals, inp.confidence)
    
    result = {
        "is_match": is_match,
        "status": status,
        "clarification_message": msg,
    }

    # ── DB Updates (Blueprint Step 6) ─────────────────────────────────────────
    if inp.session_id:
        try:
            import uuid
            from datetime import datetime
            from shared.database.db import AsyncSessionLocal
            from shared.models.is_models import ISF3icheScore
            from sqlalchemy import update

            async with AsyncSessionLocal() as session:
                # 1. Update the existing 'signals' row
                stmt = update(ISF3icheScore).where(
                    ISF3icheScore.session_id == uuid.UUID(inp.session_id),
                    ISF3icheScore.source == "signals"
                ).values(
                    user_confirmed=True,
                    is_selected=True,
                    match_status=status,
                    clarification_message=msg,
                    selected_at=datetime.utcnow()
                )
                await session.execute(stmt)

                # 2. Insert the new 'user' row
                user_score = ISF3icheScore(
                    id=uuid.uuid4(),
                    session_id=uuid.UUID(inp.session_id),
                    f3iche=inp.f3iche_user,
                    score=1.0,
                    confidence=1.0,
                    source="user",
                    is_selected=True,
                    user_confirmed=True,
                    match_status=status,
                    selected_at=datetime.utcnow()
                )
                session.add(user_score)

                await session.commit()
                activity.logger.info("  ✅ Updated signals score and inserted user F3iche score in DB.")
        except Exception as e:
            activity.logger.error("  ❌ Failed to update F3iche scores in DB: %s", e)

    activity.logger.info("✅ verify_f3iche done | status=%s match=%s", status, is_match)
    return result