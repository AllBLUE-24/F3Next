"""Map broad discovery f3iche + industry/chat hints to concrete F3iche template IDs."""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

_USE_LLM_NICHE = os.getenv("DISCOVERY_LLM_NICHE_RESOLVE", "false").lower() in (
    "1",
    "true",
    "yes",
)
_NICHE_LLM_MODEL = os.getenv("DISCOVERY_NICHE_MODEL", os.getenv("DISCOVERY_EXTRACT_MODEL", "gpt-4o-mini"))

_BROAD_CATEGORIES = frozenset({"trading", "manufacturing", "service"})

_INDUSTRY_NICHE_HINTS: List[tuple[tuple[str, ...], str]] = [
    # Specific matches first (avoid bare "chemical" → wrong niche)
    (("toll manufacturer", "toll manufacturing", "third party manufacturer", "job work challan"), "manufacturing_fabrication_jobshop"),
    (("warranty claim", "field service", "service technician", "maintenance visit", "client site breakdown", "whatsapp repair"), "service_professional"),
    (("prefabricated panel", "pre-fabricated panel", "pre fabricated panel", "screwdriver assembly", "job shop", "metal fabrication"), "manufacturing_fabrication_jobshop"),
    (("epoxy", "floor coating", "industrial coating", "paint manufacturer", "resin coating", "primer manufacturer", "chemical primer", "chemical primers"), "manufacturing_project_chemical"),
    (("adhesive", "adhesives", "sealant", "sealants", "industrial resin", "apex resins", "resins", "chemical drum", "chemical drums"), "manufacturing_project_chemical"),
    (("shelf life", "batch traceability", "batch expiry", "expiry tracking"), "manufacturing_food_batch"),
    (("chemical coating", "chemical formulation plant", "chemical plant"), "manufacturing_project_chemical"),
    (("garment", "apparel", "textile", "fabric", "stitching"), "manufacturing_garment_variants"),
    (("food", "fmcg", "dairy", "bakery"), "manufacturing_food_batch"),
    (("fabrication", "welding", "metal job"), "manufacturing_fabrication_jobshop"),
    (("fmcg", "distribution", "distributor", "wholesale"), "trading_fmcg_distributor"),
    (("hardware", "building material", "pipe", "steel trading"), "trading_hardware_variants"),
    (("auto parts", "autoparts", "spare parts", "oem"), "trading_autoparts_highvolume"),
    (("consulting", "professional services", "retainer"), "service_professional"),
]

_CHAT_NICHE_HINTS: List[tuple[tuple[str, ...], str]] = [
    (("subcontractor", "toll manufacturer", "job work", "raw material waste"), "manufacturing_fabrication_jobshop"),
    (("warranty", "field repair", "technician dispatch", "spare parts van"), "service_professional"),
    (("installation", "site work", "coating", "epoxy floor"), "manufacturing_project_chemical"),
    (("hardener", "isocyanate", "part a and part b", "moisture sensitive"), "manufacturing_project_chemical"),
    (("adhesive", "sealant", "chemical drum", "shelf life", "raw material batch", "batch traceability"), "manufacturing_project_chemical"),
    (("work in progress", "wip", "black box", "excel sheet", "batch-wise"), "manufacturing_project_chemical"),
    (("procurement", "supplier lead time", "purchase order", "material request"), "manufacturing_fabrication_jobshop"),
]

_F3ICHE_DIR = Path(__file__).parent.parent / "knowledge_base" / "common" / "f3iches"


def list_f3iche_template_ids() -> list[str]:
    if not _F3ICHE_DIR.exists():
        return []
    return sorted(p.stem for p in _F3ICHE_DIR.glob("*.json"))


def _hint_match(text: str, keywords: tuple[str, ...]) -> bool:
    t = text.lower()
    return any(kw in t for kw in keywords)


def resolve_niche_from_text(
    text: str,
    niche_ids: List[str],
    *,
    broad_f3iche: Optional[str] = None,
) -> Optional[str]:
    """Match free text (confirmation message, chat, industry) to a registry niche."""
    if not text or not text.strip():
        return None
    for keywords, niche in _INDUSTRY_NICHE_HINTS + _CHAT_NICHE_HINTS:
        if _hint_match(text, keywords):
            if broad_f3iche and niche_broad_category(niche) != broad_f3iche:
                continue
            if not niche_ids or niche in niche_ids:
                return niche
    return None


def resolve_niche_hint_from_text(
    text: str,
    *,
    broad_f3iche: Optional[str] = None,
) -> Optional[str]:
    """Match text to catalog niche id even when no F3iche template file exists yet."""
    if not text or not text.strip():
        return None
    matches: List[str] = []
    for keywords, niche in _INDUSTRY_NICHE_HINTS + _CHAT_NICHE_HINTS:
        if _hint_match(text, keywords) and niche not in matches:
            matches.append(niche)
    if not matches:
        return None
    if broad_f3iche:
        for niche in matches:
            if niche_broad_category(niche) == broad_f3iche:
                return niche
    return matches[0]


def niche_broad_category(niche_id: str) -> str:
    if niche_id.startswith("trading_"):
        return "trading"
    if niche_id.startswith("manufacturing_"):
        return "manufacturing"
    if niche_id.startswith("service_"):
        return "service"
    return niche_id


def resolve_niche_from_discovery(
    *,
    discovery_f3iche: Optional[str],
    discovery_industry: Optional[str] = None,
    chat_transcript: Optional[str] = None,
    niche_ids: List[str],
) -> Optional[str]:
    """
    Resolve a specific registry niche from broad discovery f3iche + industry/chat.

    Discovery stores trading|manufacturing|service — this maps to a concrete niche ID.
    """
    industry = (discovery_industry or "").strip()
    chat = (chat_transcript or "").strip()
    combined = f"{industry} {chat}"
    f3 = (discovery_f3iche or "").strip()

    resolved = resolve_niche_from_text(
        combined,
        niche_ids,
        broad_f3iche=f3 if f3 in _BROAD_CATEGORIES else None,
    )
    if resolved:
        return resolved

    if f3 in niche_ids:
        return f3

    if f3 in _BROAD_CATEGORIES:
        prefix = f"{f3}_"
        candidates = [n for n in niche_ids if n.startswith(prefix)]
        if len(candidates) == 1:
            return candidates[0]

    return None


def resolve_discovery_f3iche_niche(
    *,
    discovery_f3iche: str,
    industry: str = "",
    chat_transcript: str = "",
) -> str:
    """Map trading|manufacturing|service to a template under common/f3iches/."""
    niche_ids = list_f3iche_template_ids()
    combined = f"{industry} {chat_transcript}".strip()
    broad = discovery_f3iche if discovery_f3iche in _BROAD_CATEGORIES else None

    category_hint = resolve_niche_hint_from_text(combined, broad_f3iche=broad)
    if category_hint:
        if f3iche_template_exists(category_hint) or broad:
            return category_hint

    strong_hint = resolve_niche_hint_from_text(combined)
    if strong_hint and f3iche_template_exists(strong_hint):
        return strong_hint

    resolved = resolve_niche_from_discovery(
        discovery_f3iche=discovery_f3iche,
        discovery_industry=industry,
        chat_transcript=chat_transcript,
        niche_ids=niche_ids,
    )
    if resolved:
        return resolved
    if discovery_f3iche in niche_ids:
        return discovery_f3iche
    if niche_ids:
        prefix = f"{discovery_f3iche}_" if discovery_f3iche else ""
        matches = [n for n in niche_ids if n.startswith(prefix)] if prefix else niche_ids
        if matches:
            return matches[0]
        if hinted:
            return hinted
        if discovery_f3iche in _BROAD_CATEGORIES:
            return discovery_f3iche
    return discovery_f3iche or "manufacturing_project_chemical"


def _parse_llm_json(content: str) -> dict:
    start_idx = content.find("{")
    end_idx = content.rfind("}")
    if start_idx != -1 and end_idx != -1:
        clean_json = content[start_idx : end_idx + 1]
    else:
        clean_json = content.replace("```json", "").replace("```", "").strip()
    return json.loads(clean_json)


def infer_broad_f3iche(
    *,
    f3iche_hint: Optional[str] = None,
    industry: str = "",
    coverage: Optional[dict] = None,
) -> str:
    """Map extraction hints to trading|manufacturing|service."""
    hint = (f3iche_hint or "").strip().lower()
    if hint in _BROAD_CATEGORIES:
        return hint

    industry_val = industry.strip()
    if not industry_val and coverage:
        industry_val = str((coverage.get("industry") or {}).get("value") or "")

    lowered = industry_val.lower()
    if "manufactur" in lowered or "factory" in lowered or "production" in lowered:
        return "manufacturing"
    if any(x in lowered for x in ("service", "consult", "facility", "maintenance")):
        return "service"
    return "trading"


def _coverage_summary_for_niche(coverage: Optional[dict]) -> str:
    if not coverage:
        return "(none)"
    lines: list[str] = []
    for key in ("industry", "strategy", "scale", "legacy_system", "pain_point"):
        entry = coverage.get(key) or {}
        val = entry.get("value")
        if val:
            lines.append(f"  • {key}: {val}")
    return "\n".join(lines) if lines else "(none)"


async def resolve_discovery_f3iche_niche_with_llm(
    *,
    discovery_f3iche: str,
    industry: str = "",
    chat_transcript: str = "",
    coverage: Optional[dict] = None,
) -> Optional[str]:
    """LLM picks a niche id from the registry. Returns None on failure."""
    from containers.discovery.prompts.niche import NICHE_RESOLUTION_PROMPT
    from llm_router import invoke_smart_llm

    niche_ids = list_f3iche_template_ids()
    if not niche_ids:
        return None

    prompt = NICHE_RESOLUTION_PROMPT.format(
        transcript=chat_transcript or "(empty)",
        coverage_summary=_coverage_summary_for_niche(coverage),
        broad_f3iche=discovery_f3iche,
        industry=industry or "(unknown)",
        niche_id_list="\n".join(f"  - {nid}" for nid in niche_ids),
    )

    response = await invoke_smart_llm(
        [("human", prompt)],
        model_name=_NICHE_LLM_MODEL,
        temperature=0.1,
        max_output_tokens=300,
        response_mime_type="application/json",
    )
    raw = _parse_llm_json(response.content or "")
    niche_id = str(raw.get("f3iche_niche_id") or raw.get("niche_id") or "").strip()
    if niche_id in niche_ids:
        return niche_id
    logger.warning("LLM niche %r not in registry; ignoring", niche_id)
    return None


async def resolve_discovery_f3iche_niche_async(
    *,
    discovery_f3iche: str,
    industry: str = "",
    chat_transcript: str = "",
    coverage: Optional[dict] = None,
    use_llm_niche: Optional[bool] = None,
) -> Tuple[str, str]:
    """
    Resolve concrete F3iche niche id.

    Returns (niche_id, source) where source is 'llm' or 'keyword'.
    """
    use_llm = _USE_LLM_NICHE if use_llm_niche is None else use_llm_niche

    if use_llm:
        try:
            llm_niche = await resolve_discovery_f3iche_niche_with_llm(
                discovery_f3iche=discovery_f3iche,
                industry=industry,
                chat_transcript=chat_transcript,
                coverage=coverage,
            )
            if llm_niche:
                return llm_niche, "llm"
        except Exception as e:
            logger.warning("LLM niche resolution failed, using keyword fallback: %s", e)

    keyword_niche = resolve_discovery_f3iche_niche(
        discovery_f3iche=discovery_f3iche,
        industry=industry,
        chat_transcript=chat_transcript,
    )
    return keyword_niche, "keyword"


def f3iche_template_path(f3iche_id: str) -> Path:
    """Expected path for a niche template — never silently substitutes another file."""
    return _F3ICHE_DIR / f"{f3iche_id}.json"


def f3iche_template_exists(f3iche_id: str) -> bool:
    return f3iche_template_path(f3iche_id).is_file()


def f3iche_template_status(f3iche_id: str) -> dict[str, object]:
    """Report whether the resolved niche has a template on disk."""
    path = f3iche_template_path(f3iche_id)
    return {
        "niche_id": f3iche_id,
        "template_available": path.is_file(),
        "template_path": str(path),
        "broad_category": niche_broad_category(f3iche_id),
    }

def discovery_evidence_bullets(
    *,
    discovery_f3iche: Optional[str],
    discovery_industry: Optional[str] = None,
    headline: Optional[str] = None,
    chat_transcript: Optional[str] = None,
    max_bullets: int = 3,
) -> List[str]:
    """Build user-facing discovery evidence for synthesis fallback."""
    bullets: List[str] = []
    if discovery_industry:
        bullets.append(f"Discovery industry: {discovery_industry}")
    if discovery_f3iche:
        bullets.append(f"Discovery business type: {discovery_f3iche}")
    if headline:
        bullets.append(headline)
    if chat_transcript:
        for line in chat_transcript.splitlines()[-6:]:
            line = line.strip()
            if line and len(line) > 12:
                bullets.append(line if len(line) <= 120 else line[:117] + "...")
            if len(bullets) >= max_bullets:
                break
    return bullets[:max_bullets]
