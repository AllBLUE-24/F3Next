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


def _load_manifest_from_r2(r2_manifest_url: str) -> Dict:
    """Download the full manifest from R2 (v2 or legacy v1)."""
    if not r2_manifest_url or r2_manifest_url.startswith("error:"):
        return {}
    try:
        s3 = _get_s3_client()
        response = s3.get_object(Bucket="clean-data", Key=r2_manifest_url)
        return json.loads(response["Body"].read().decode("utf-8"))
    except Exception as e:
        activity.logger.error("  ❌ Failed to load manifest from R2: %s", e)
        return {}


def _load_file_contents_from_r2(r2_manifest_url: str) -> Dict[str, str]:
    """Download the file contents manifest from R2 and return {filename: content}."""
    from containers.implementation.file_io.manifest_utils import extract_files_from_manifest

    manifest = _load_manifest_from_r2(r2_manifest_url)
    return extract_files_from_manifest(manifest)


class _SignalsInferenceService:
    def __init__(self):
        self._registry: Optional[Dict] = None

    def _load_registry(self) -> Dict:
        if self._registry is None:
            from containers.implementation.signals_agent.signals_scorer import load_signals_registry
            self._registry = load_signals_registry()
        return self._registry

    def _registry_summary(self) -> Dict:
        reg = self._load_registry()
        return {
            "niche_ids": reg.get("_meta", {}).get("niche_ids", []),
            "niche_definitions": reg.get("niche_score_to_id_map", {}),
        }

    def infer_f3iche(
        self,
        uploaded_files: List[Dict],
        file_contents: Optional[Dict[str, str]] = None,
        corpus_understanding: Optional[Dict] = None,
        file_meta: Optional[Dict] = None,
        discovery_f3iche: Optional[str] = None,
    ) -> tuple[str, float, List[str], str, Dict]:
        """
        Tiered inference: registry rules → LLM (if ambiguous) → blend.

        Returns: (f3iche, confidence, signals, method, registry_result)
        """
        from containers.implementation.signals_agent.prompts import F3ICHE_INFERENCE_PROMPT
        from containers.implementation.signals_agent.signals_scorer import (
            apply_discovery_prior,
            blend_llm_with_registry,
            score_manifest,
        )
        from containers.implementation.utils.llm_helper import generate_json

        registry = self._load_registry()
        registry_summary = self._registry_summary()
        niche_ids = registry_summary.get("niche_ids", [])

        filenames = [f.get("file_name", f.get("name", "")) for f in uploaded_files]
        contents = file_contents or {}

        # ── Step A: deterministic registry scoring ───────────────────────────
        registry_result = score_manifest(
            filenames=filenames,
            file_meta=file_meta or {},
            file_contents=contents,
            registry=registry,
        )
        registry_result = apply_discovery_prior(registry_result, discovery_f3iche)

        registry_hits = registry_result.get("hits") or []
        hit_summaries = [
            f"[{h.get('signal_type')}] {h.get('found_in')}: '{h.get('pattern')}' "
            f"→ {h.get('suggests_f3iche')} ({h.get('direction')}, w={h.get('weight')})"
            for h in registry_hits[:20]
        ]

        # If registry is confident, use it directly (no LLM call)
        if registry_result.get("confident"):
            reg_top = registry_result["top_niche"]
            reg_conf = float(registry_result["confidence"])
            signals = hit_summaries[:5] + [
                f"[registry] {registry_result['signal_count']} signals, margin={registry_result['margin']}"
            ]
            if discovery_f3iche:
                signals.append(f"[discovery_prior] user stated: {discovery_f3iche}")
            activity.logger.info(
                "  Registry confident → %s (%.0f%%, %d hits)",
                reg_top, reg_conf * 100, registry_result["signal_count"],
            )
            return reg_top, reg_conf, signals, "registry", registry_result

        # ── Step B: LLM for ambiguous cases ──────────────────────────────────
        file_summaries = []
        for fname in filenames:
            text = contents.get(fname, "")
            meta = (file_meta or {}).get(fname) or {}
            cols = meta.get("columns") or []
            samples = meta.get("sample_rows") or []
            snippet = text[:1500] if text else "(empty file)"
            file_summaries.append(
                f"Filename: {fname}\n"
                f"Columns: {json.dumps(cols)}\n"
                f"Sample Rows: {json.dumps(samples[:2])}\n"
                f"Content Snippet:\n{snippet}\n---"
            )

        corpus_block = (
            json.dumps(corpus_understanding, indent=2)
            if corpus_understanding
            else "(not available — rely on registry scores and file data)"
        )

        prompt = F3ICHE_INFERENCE_PROMPT.format(
            niche_catalog=json.dumps(registry_summary, indent=2),
            discovery_f3iche=discovery_f3iche or "(none)",
            registry_scores=json.dumps(registry_result.get("niche_scores") or {}, indent=2),
            hit_count=registry_result.get("signal_count", 0),
            registry_hits="\n".join(hit_summaries) or "(no registry hits)",
            filenames=json.dumps(filenames),
            file_summaries="".join(file_summaries),
            corpus_block=corpus_block,
        )

        llm_f3iche = registry_result.get("top_niche") or "trading_fmcg_distributor"
        llm_confidence = float(registry_result.get("confidence") or 0.0)
        signals: List[str] = hit_summaries[:3]

        try:
            result = generate_json(prompt, temperature=0.1, max_output_tokens=4000)
            llm_f3iche = result.get("f3iche", llm_f3iche)
            if llm_f3iche not in niche_ids:
                llm_f3iche = registry_result.get("top_niche") or niche_ids[0]
            llm_confidence = float(result.get("confidence", llm_confidence))
            llm_signals = result.get("collected_signals") or []
            method_note = result.get("method_note", "")
            signals = list(llm_signals) + hit_summaries[:2]
            if method_note:
                signals.append(f"[llm] {method_note}")
        except Exception as e:
            activity.logger.error("  LLM inference failed, using registry top: %s", e)
            signals.append(f"[fallback] LLM failed: {e}")

        # ── Step C: blend registry + LLM ─────────────────────────────────────
        final_f3iche, final_conf, method = blend_llm_with_registry(
            registry_result=registry_result,
            llm_f3iche=llm_f3iche,
            llm_confidence=llm_confidence,
        )
        if discovery_f3iche and final_f3iche == discovery_f3iche:
            signals.append(f"[discovery_prior] aligned with user-stated: {discovery_f3iche}")

        return final_f3iche, final_conf, signals, method, registry_result



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
    discovery_f3iche: Optional[str] = None


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
    
    # Load full manifest from R2 (v2 includes file_meta + corpus_understanding)
    manifest = _load_manifest_from_r2(inp.r2_manifest_url)
    file_contents = _load_file_contents_from_r2(inp.r2_manifest_url)
    activity.logger.info("  Loaded %d file contents from R2 manifest", len(file_contents))

    discovery_f3iche = inp.discovery_f3iche
    if not discovery_f3iche and inp.session_id:
        try:
            import uuid
            from sqlalchemy import select
            from shared.database.db import AsyncSessionLocal
            from shared.models.is_models import ISSession

            async with AsyncSessionLocal() as db:
                row = (await db.execute(
                    select(ISSession).where(ISSession.id == uuid.UUID(inp.session_id))
                )).scalar_one_or_none()
                if row and row.discovery_f3iche:
                    discovery_f3iche = row.discovery_f3iche
                    activity.logger.info("  Discovery prior loaded: %s", discovery_f3iche)
        except Exception as e:
            activity.logger.debug("  Could not load discovery_f3iche: %s", e)

    svc = _SignalsInferenceService()
    f3iche_id, confidence, signals, method, registry_result = svc.infer_f3iche(
        inp.uploaded_files,
        file_contents,
        corpus_understanding=manifest.get("corpus_understanding"),
        file_meta=manifest.get("file_meta"),
        discovery_f3iche=discovery_f3iche,
    )

    # Semantic cross-check via kb_embeddings (async-safe)
    try:
        import re as _re
        from containers.implementation.utils.rag_helper import rag_retrieve

        summaries = []
        for fname, text in file_contents.items():
            summaries.append(f"{fname}: {(text or '')[:500]}")
        content_summary = " ".join(summaries)[:1500]
        semantic_hits = await rag_retrieve(content_summary, "f3iche_", top_k=3)
        semantic_candidates: list[str] = []
        for chunk in semantic_hits:
            m = _re.search(r"F3iche ID:\s*(\S+)", chunk)
            if m:
                semantic_candidates.append(m.group(1).strip())
        if semantic_candidates and semantic_candidates[0] != f3iche_id:
            activity.logger.info(
                "  [RAG cross-check] LLM inferred '%s' but top semantic match is '%s'",
                f3iche_id, semantic_candidates[0],
            )
            signals = list(signals) + [
                f"[RAG] Semantic match suggests '{semantic_candidates[0]}' as alternative — "
                "confirm with user if unsure."
            ]
    except Exception as rag_e:
        activity.logger.debug("  [RAG cross-check] skipped: %s", rag_e)

    result = {
        "f3iche": f3iche_id,
        "confidence": round(confidence, 2),
        "collected_signals": signals,
        "inference_method": method,
        "registry_signal_count": registry_result.get("signal_count", 0),
        "registry_confident": registry_result.get("confident", False),
        "registry_scores": registry_result.get("niche_scores") or {},
    }

    # ── Persist to DB (v2 schema) ────────────────────────────────────────────
    if inp.session_id:
        try:
            import uuid
            from shared.database.db import AsyncSessionLocal
            from shared.models.is_models import ISFileSignal, ISF3icheScore

            async with AsyncSessionLocal() as session:
                # Registry rule hits (deterministic)
                for hit in registry_result.get("hits") or []:
                    session.add(ISFileSignal(
                        id=uuid.uuid4(),
                        session_id=uuid.UUID(inp.session_id),
                        signal_type=hit.get("signal_type") or "registry",
                        pattern_matched=str(hit.get("pattern") or ""),
                        suggests_f3iche=hit.get("suggests_f3iche") or f3iche_id,
                        weight=float(hit.get("weight") or 0.0),
                        confidence=confidence,
                        found_in=hit.get("found_in"),
                    ))

                hit_patterns = {str(h.get("pattern") or "") for h in (registry_result.get("hits") or [])}
                # Narrative signals (LLM / blended summary)
                for sig_text in signals:
                    if any(pat and pat in sig_text for pat in hit_patterns):
                        continue
                    session.add(ISFileSignal(
                        id=uuid.uuid4(),
                        session_id=uuid.UUID(inp.session_id),
                        signal_type="inference_summary",
                        pattern_matched=sig_text[:500],
                        suggests_f3iche=f3iche_id,
                        weight=1.0,
                        confidence=confidence,
                    ))

                # All niche scores from registry
                for niche, score in (registry_result.get("niche_scores") or {}).items():
                    if score > 0:
                        session.add(ISF3icheScore(
                            id=uuid.uuid4(),
                            session_id=uuid.UUID(inp.session_id),
                            f3iche=niche,
                            score=score,
                            confidence=score,
                            source="registry",
                            is_selected=(niche == f3iche_id),
                        ))

                # Selected inference row
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

    activity.logger.info(
        "✅ infer_f3iche done | %s (%.0f%%) method=%s signals=%d registry_hits=%d",
        f3iche_id, confidence * 100, method, len(signals), registry_result.get("signal_count", 0),
    )
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