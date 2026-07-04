"""Backward-compatible re-exports — canonical module is containers.discovery.niche_resolver."""
from containers.discovery.niche_resolver import (
    discovery_evidence_bullets,
    niche_broad_category,
    resolve_discovery_f3iche_niche,
    resolve_niche_from_discovery,
    resolve_niche_from_text,
)

__all__ = [
    "discovery_evidence_bullets",
    "niche_broad_category",
    "resolve_discovery_f3iche_niche",
    "resolve_niche_from_discovery",
    "resolve_niche_from_text",
]
