"""Map broad discovery f3iche + industry/chat hints to specific registry niche IDs."""
from __future__ import annotations

import re
from typing import List, Optional

_BROAD_CATEGORIES = frozenset({"trading", "manufacturing", "service"})

_INDUSTRY_NICHE_HINTS: List[tuple[tuple[str, ...], str]] = [
    (("chemical", "coating", "epoxy", "floor", "paint", "primer", "resin", "adhesive"), "manufacturing_project_chemical"),
    (("garment", "apparel", "textile", "fabric", "stitching"), "manufacturing_garment_variants"),
    (("food", "batch", "fmcg", "dairy", "bakery"), "manufacturing_food_batch"),
    (("fabrication", "job shop", "jobshop", "welding", "metal"), "manufacturing_fabrication_jobshop"),
    (("fmcg", "distribution", "distributor", "wholesale"), "trading_fmcg_distributor"),
    (("hardware", "building material", "pipe", "steel"), "trading_hardware_variants"),
    (("auto parts", "autoparts", "spare parts", "oem"), "trading_autoparts_highvolume"),
    (("consulting", "professional", "services", "retainer"), "service_professional"),
]

_CHAT_NICHE_HINTS: List[tuple[tuple[str, ...], str]] = [
    (("installation", "project", "site work", "coating", "epoxy", "floor"), "manufacturing_project_chemical"),
    (("purchase order", "raw material", "rm-", "vendor"), "manufacturing_project_chemical"),
]


def niche_broad_category(niche_id: str) -> str:
    if niche_id.startswith("trading_"):
        return "trading"
    if niche_id.startswith("manufacturing_"):
        return "manufacturing"
    if niche_id.startswith("service_"):
        return "service"
    return niche_id


def _hint_match(text: str, keywords: tuple[str, ...]) -> bool:
    t = text.lower()
    return any(kw in t for kw in keywords)


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

    for keywords, niche in _INDUSTRY_NICHE_HINTS:
        if niche in niche_ids and _hint_match(combined, keywords):
            return niche

    for keywords, niche in _CHAT_NICHE_HINTS:
        if niche in niche_ids and _hint_match(chat, keywords):
            return niche

    f3 = (discovery_f3iche or "").strip()
    if f3 in niche_ids:
        return f3

    if f3 in _BROAD_CATEGORIES:
        prefix = f"{f3}_"
        candidates = [n for n in niche_ids if n.startswith(prefix)]
        if len(candidates) == 1:
            return candidates[0]

    return None


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
