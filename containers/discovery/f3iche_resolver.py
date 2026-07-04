"""Backward-compatible re-exports — use containers.discovery.niche_resolver."""
from containers.discovery.niche_resolver import (
    f3iche_template_path,
    list_f3iche_template_ids,
    resolve_discovery_f3iche_niche,
)

__all__ = [
    "f3iche_template_path",
    "list_f3iche_template_ids",
    "resolve_discovery_f3iche_niche",
]
