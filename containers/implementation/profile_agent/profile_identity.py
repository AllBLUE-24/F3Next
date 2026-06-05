"""Resolve company identity fields for profile build from discovery + synthesis."""
from __future__ import annotations

import re
from typing import Any, Dict, Optional


_BROAD_INDUSTRIES = frozenset({"manufacturing", "trading", "service", "general"})


def slug_to_display_name(company_slug: Optional[str]) -> Optional[str]:
    if not company_slug or company_slug in ("unknown", ""):
        return None
    return company_slug.replace("-", " ").replace("_", " ").strip().title()


def resolve_profile_identity(
    *,
    company_slug: Optional[str] = None,
    company_name: Optional[str] = None,
    industry: Optional[str] = None,
    industry_sub: Optional[str] = None,
    company_size: Optional[str] = None,
    discovery_ctx: Optional[Dict[str, Any]] = None,
    synthesis: Optional[Dict[str, Any]] = None,
) -> Dict[str, Optional[str]]:
    """
    Fill profile identity from discovery/synthesis when the confirm signal left gaps.

    discovery_ctx: output of load_discovery_context()
    synthesis: f3iche_confirmation proposal from Step 3.5
    """
    ctx = discovery_ctx or {}
    meta = ctx.get("discovery_metadata") or {}
    coverage = meta.get("coverage") if isinstance(meta.get("coverage"), dict) else {}
    synth = synthesis or {}

    resolved_name = (company_name or "").strip() or None
    if not resolved_name:
        resolved_name = (meta.get("company_name") or "").strip() or None
    if not resolved_name:
        resolved_name = slug_to_display_name(company_slug)

    resolved_industry = (industry or synth.get("proposed_industry") or meta.get("industry") or "").strip()
    if not resolved_industry:
        resolved_industry = "general"

    discovery_industry = (
        (ctx.get("discovery_industry") or meta.get("industry") or "").strip()
    )
    resolved_sub = (industry_sub or "").strip() or None
    if discovery_industry and discovery_industry.lower() not in _BROAD_INDUSTRIES:
        resolved_sub = resolved_sub or discovery_industry
    elif discovery_industry and resolved_industry.lower() in _BROAD_INDUSTRIES:
        resolved_sub = resolved_sub or discovery_industry

    resolved_size = (company_size or "").strip() or None
    if not resolved_size:
        scale_val = (coverage.get("scale") or {}).get("value") if isinstance(coverage.get("scale"), dict) else None
        if scale_val:
            resolved_size = str(scale_val).strip()

    return {
        "company_name": resolved_name,
        "industry": resolved_industry,
        "industry_sub": resolved_sub,
        "company_size": resolved_size,
    }
