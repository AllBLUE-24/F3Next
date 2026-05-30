"""
Live Entity Registry (LER) — shared resolution for IS and OS.

CVS may suggest; LER decides. See docs/v1.0.0/OPERATING_MODEL.md.
"""

from shared.entity_resolution.gaps import resolution_gaps_from_unresolved
from shared.entity_resolution.ler import (
    BRAIN_VERSION,
    apply_resolved_to_intent,
    build_link_cache,
    build_resolution_map,
    fetch_link_cache_for_doctypes,
)
from shared.entity_resolution.resolve import (
    ResolvedEntities,
    resolve_entities_batch,
    resolve_links_for_command,
)
from shared.entity_resolution.snapshot import brain_snapshot_keys
from shared.entity_resolution.targets import collect_link_targets_from_intent

__all__ = [
    "BRAIN_VERSION",
    "ResolvedEntities",
    "apply_resolved_to_intent",
    "brain_snapshot_keys",
    "build_link_cache",
    "build_resolution_map",
    "collect_link_targets_from_intent",
    "fetch_link_cache_for_doctypes",
    "resolution_gaps_from_unresolved",
    "resolve_entities_batch",
    "resolve_links_for_command",
]
