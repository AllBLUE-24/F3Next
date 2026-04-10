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
from typing import Dict, List, Optional, Tuple

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
    ) -> Tuple[str, float, List[str]]:
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
    NORMALIZE_MAP = {
        "trading":       ["trading", "trade", "distributor", "trader", "trading_fmcg_distributor",
                          "trading_hardware_variants", "trading_autoparts_highvolume"],
        "manufacturing": ["manufacturing", "manufacture", "production", "maker",
                          "manufacturing_garment_variants", "manufacturing_food_batch",
                          "manufacturing_fabrication_jobshop"],
        "service":       ["service", "services", "consulting", "service_professional"],
    }

    @classmethod
    def normalize(cls, f3iche: str) -> str:
        if not f3iche:
            return ""
        f = f3iche.lower().strip()
        for canonical, aliases in cls.NORMALIZE_MAP.items():
            if f == canonical or f in aliases:
                return canonical
        return f

    @classmethod
    def verify(cls, f3iche_user: str, f3iche_signals: str, confidence: float = 0.0) -> Tuple[bool, str, Optional[str]]:
        u, s = cls.normalize(f3iche_user), cls.normalize(f3iche_signals)
        if not u:
            return (False, "pending_clarification", "Please confirm your business type from the discovery chat.")
        if not s:
            return (True, "matched", None)
        if u == s:
            return (True, "matched", None)
        msg = (
            f"Our analysis suggests you might be a **{s}** business, "
            f"but you indicated **{u}**. Could you clarify which best describes your operations?"
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
    activity.logger.info("✅ verify_f3iche done | status=%s match=%s", status, is_match)
    return result