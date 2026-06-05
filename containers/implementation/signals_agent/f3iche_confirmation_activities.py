"""
F3iche confirmation synthesis (Step 3.5).

Merges file inference + discovery chat/metadata into a user-facing confirmation
proposal before the f3iche_confirmed signal gate.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from temporalio import activity

from containers.implementation.signals_agent.discovery_context import load_discovery_context
from containers.implementation.signals_agent.f3iche_confirmation_models import (
    F3icheConfirmationSynthesis,
    F3icheCorrectionResolution,
)
from containers.implementation.signals_agent.f3iche_confirmation_prompts import (
    F3ICHE_CONFIRMATION_PROMPT,
    F3ICHE_CORRECTION_PROMPT,
)
from containers.implementation.signals_agent.signals_scorer import load_signals_registry
from shared.database.db import AsyncSessionLocal
from shared.models.is_models import ISAuditTrail, ISF3icheScore, ISSession
from shared.structured_llm import generate_typed

_KB = Path(__file__).resolve().parent.parent.parent / "knowledge_base" / "common"
_DISPLAY_NAMES: Dict[str, str] = {
    "trading_fmcg_distributor": "FMCG Distribution",
    "trading_hardware_variants": "Hardware / Building Materials Trading",
    "trading_autoparts_highvolume": "Auto Parts Distribution",
    "manufacturing_garment_variants": "Garment Manufacturing",
    "manufacturing_food_batch": "Food / Batch Manufacturing",
    "manufacturing_fabrication_jobshop": "Metal Fabrication / Job Shop",
    "manufacturing_project_chemical": "Chemical Coatings Manufacturer & Project Installer",
    "service_professional": "Professional Services",
}


def _display_name_for(f3iche: str) -> str:
    return _DISPLAY_NAMES.get(f3iche, f3iche.replace("_", " ").title())


@dataclass
class SynthesizeF3icheConfirmationInput:
    session_id: str
    project_id: str
    infer_result: Dict[str, Any]
    r2_manifest_url: Optional[str] = None
    registry_result: Optional[Dict[str, Any]] = None
    corpus_understanding: Optional[Dict[str, Any]] = None


@dataclass
class ResolveF3icheCorrectionInput:
    correction_text: str
    synthesis: Dict[str, Any]
    session_id: Optional[str] = None


async def _persist_synthesis(session_id: str, synthesis: Dict[str, Any]) -> None:
    async with AsyncSessionLocal() as db:
        db.add(ISAuditTrail(
            id=uuid.uuid4(),
            session_id=uuid.UUID(session_id),
            action="f3iche_confirmation_synthesized",
            actor="llm",
            details=synthesis,
            result="success",
        ))
        # Proposed niche row for API/history
        db.add(ISF3icheScore(
            id=uuid.uuid4(),
            session_id=uuid.UUID(session_id),
            f3iche=synthesis.get("proposed_f3iche", ""),
            score=float(synthesis.get("confidence") or 0.0),
            confidence=float(synthesis.get("confidence") or 0.0),
            source="synthesis",
            is_selected=False,
            clarification_message=synthesis.get("confirmation_message"),
        ))
        await db.commit()


async def synthesize_f3iche_confirmation_core(
    inp: SynthesizeF3icheConfirmationInput,
) -> Dict[str, Any]:
    """Core synthesis logic (callable from activity or tests)."""
    registry = load_signals_registry()
    niche_ids: List[str] = registry.get("_meta", {}).get("niche_ids") or []

    discovery_ctx: Dict[str, Any] = {}
    async with AsyncSessionLocal() as db:
        sess = (await db.execute(
            select(ISSession).where(ISSession.id == uuid.UUID(inp.session_id))
        )).scalar_one_or_none()
        discovery_ctx = await load_discovery_context(
            db, project_id=inp.project_id, session_row=sess,
        )

    corpus = inp.corpus_understanding
    if not corpus and inp.r2_manifest_url:
        try:
            from containers.implementation.signals_agent.activities import _load_manifest_from_r2
            manifest = _load_manifest_from_r2(inp.r2_manifest_url)
            corpus = manifest.get("corpus_understanding")
        except Exception:
            corpus = {}
    corpus = corpus or {}
    registry_scores = (inp.registry_result or {}).get("niche_scores") or inp.infer_result.get("registry_scores") or {}

    prompt = F3ICHE_CONFIRMATION_PROMPT.format(
        niche_ids=json.dumps(niche_ids),
        file_inference=json.dumps(inp.infer_result, indent=2, default=str),
        registry_scores=json.dumps(registry_scores, indent=2),
        corpus_summary=json.dumps(corpus.get("corpus_summary") or "", default=str),
        discovery_metadata=json.dumps(discovery_ctx.get("discovery_metadata") or {}, indent=2, default=str),
        chat_transcript=discovery_ctx.get("chat_transcript") or "(no discovery chat)",
    )

    try:
        raw = await generate_typed(
            prompt=prompt,
            schema=F3icheConfirmationSynthesis,
            temperature=0.15,
            max_output_tokens=3000,
        )
        synthesis = F3icheConfirmationSynthesis.model_validate(raw)
    except Exception as e:
        import logging
        logging.getLogger(__name__).error("F3iche synthesis LLM failed: %s", e)
        proposed = inp.infer_result.get("f3iche") or "trading_fmcg_distributor"
        if proposed not in niche_ids:
            proposed = registry_scores and max(registry_scores, key=registry_scores.get) or niche_ids[0]
        industry = (
            discovery_ctx.get("discovery_industry")
            or discovery_ctx.get("discovery_metadata", {}).get("industry")
            or "general"
        )
        synthesis = F3icheConfirmationSynthesis(
            confirmation_message=(
                f"We analyzed your files and think your business is {_display_name_for(proposed)}. "
                f"Is that correct?"
            ),
            proposed_f3iche=proposed,
            proposed_industry=industry,
            display_name=_display_name_for(proposed),
            confidence=float(inp.infer_result.get("confidence") or 0.5),
            evidence_from_files=inp.infer_result.get("collected_signals", [])[:4],
            evidence_from_discovery=[],
            conflicts=[f"Synthesis fallback: {e}"],
            alignment="partial",
        )

    if synthesis.proposed_f3iche not in niche_ids:
        fallback = inp.infer_result.get("f3iche") or niche_ids[0]
        synthesis.proposed_f3iche = fallback if fallback in niche_ids else niche_ids[0]
        synthesis.display_name = _display_name_for(synthesis.proposed_f3iche)

    result = synthesis.model_dump()
    result["inferred_f3iche"] = inp.infer_result.get("f3iche")
    result["inference_method"] = inp.infer_result.get("inference_method")
    result["discovery_f3iche"] = discovery_ctx.get("discovery_f3iche")
    result["discovery_industry"] = discovery_ctx.get("discovery_industry")
    result["mvp_focus"] = discovery_ctx.get("mvp_focus")

    await _persist_synthesis(inp.session_id, result)
    return result


@activity.defn(name="synthesize_f3iche_confirmation")
async def synthesize_f3iche_confirmation(inp: SynthesizeF3icheConfirmationInput) -> Dict[str, Any]:
    activity.logger.info("▶ synthesize_f3iche_confirmation | session=%s", inp.session_id)
    result = await synthesize_f3iche_confirmation_core(inp)
    activity.logger.info(
        "  ✅ Proposed %s (%.0f%%) alignment=%s",
        result.get("proposed_f3iche"),
        float(result.get("confidence") or 0) * 100,
        result.get("alignment"),
    )
    return result


async def resolve_f3iche_correction_core(inp: ResolveF3icheCorrectionInput) -> Dict[str, Any]:
    registry = load_signals_registry()
    niche_ids: List[str] = registry.get("_meta", {}).get("niche_ids") or []

    prompt = F3ICHE_CORRECTION_PROMPT.format(
        niche_ids=json.dumps(niche_ids),
        proposed_f3iche=inp.synthesis.get("proposed_f3iche", ""),
        proposed_industry=inp.synthesis.get("proposed_industry", ""),
        confirmation_message=inp.synthesis.get("confirmation_message", ""),
        correction_text=inp.correction_text,
    )

    try:
        raw = await generate_typed(
            prompt=prompt,
            schema=F3icheCorrectionResolution,
            temperature=0.1,
            max_output_tokens=1500,
        )
        resolved = F3icheCorrectionResolution.model_validate(raw)
    except Exception as e:
        import logging
        logging.getLogger(__name__).error("Correction resolution failed: %s", e)
        return {
            "f3iche": inp.synthesis.get("proposed_f3iche", niche_ids[0]),
            "industry": inp.synthesis.get("proposed_industry", "general"),
            "display_name": inp.synthesis.get("display_name", ""),
            "reasoning": f"Fallback to proposal: {e}",
        }

    if resolved.f3iche not in niche_ids:
        resolved.f3iche = inp.synthesis.get("proposed_f3iche") or niche_ids[0]

    return resolved.model_dump()


@activity.defn(name="resolve_f3iche_correction")
async def resolve_f3iche_correction(inp: ResolveF3icheCorrectionInput) -> Dict[str, Any]:
    activity.logger.info("▶ resolve_f3iche_correction")
    return await resolve_f3iche_correction_core(inp)
