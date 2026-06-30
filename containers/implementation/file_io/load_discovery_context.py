"""
File IO Agent — Load discovery metadata from hooks table.

P1 Optimization: Reads pre-confirmed f3iche and discovery context
from hooks.discovery_metadata instead of re-inferring in IS workflow.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional
from uuid import UUID

from temporalio import activity
from sqlalchemy import select

from shared.database.db import AsyncSessionLocal
from shared.models.hooks import Hook


@dataclass
class LoadDiscoveryContextInput:
    project_id: str


@activity.defn(name="load_discovery_context")
async def load_discovery_context(inp: LoadDiscoveryContextInput) -> Dict[str, Any]:
    """
    Load discovery_metadata from hooks table.
    
    Returns:
        - f3iche: str (e.g., "process_mfg_batch", "trading")
        - industry: str
        - mvp_focus: dict with primary_bottleneck and functional_requirements
        - industry_sub: str (optional)
        - company_name: str (optional)
        - company_size: str (optional)
        - source: "discovery" or "defaults"
    """
    activity.logger.info("▶ load_discovery_context | project_id=%s", inp.project_id)
    
    try:
        async with AsyncSessionLocal() as db:
            hook_row = (
                await db.execute(
                    select(Hook).where(Hook.project_id == UUID(inp.project_id))
                )
            ).scalar_one_or_none()
            
            if hook_row and hook_row.discovery_metadata:
                discovery_metadata = hook_row.discovery_metadata
                
                f3iche = discovery_metadata.get("f3iche", "trading")
                industry = discovery_metadata.get("industry", "general")
                
                activity.logger.info("  ✅ Discovery context loaded | f3iche=%s industry=%s", f3iche, industry)
                
                return {
                    "f3iche": f3iche,
                    "industry": industry,
                    "mvp_focus": discovery_metadata.get("mvp_focus", {}),
                    "industry_sub": discovery_metadata.get("industry_sub"),
                    "company_name": discovery_metadata.get("company_name"),
                    "company_size": discovery_metadata.get("company_size"),
                    "source": "discovery",
                }
            else:
                activity.logger.warning("  ⚠️ No discovery_metadata found for project %s — using defaults", inp.project_id)
                return {
                    "f3iche": "trading",
                    "industry": "general",
                    "mvp_focus": {},
                    "industry_sub": None,
                    "company_name": None,
                    "company_size": None,
                    "source": "defaults",
                }
    
    except Exception as e:
        activity.logger.error("  ❌ Failed to load discovery context: %s", e)
        # Return defaults on error (non-fatal)
        return {
            "f3iche": "trading",
            "industry": "general",
            "mvp_focus": {},
            "industry_sub": None,
            "company_name": None,
            "company_size": None,
            "source": "error_fallback",
        }
