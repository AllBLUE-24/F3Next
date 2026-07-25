"""Backward-compatible re-exports — use containers.discovery.niche_resolver."""
from containers.discovery.niche_resolver import (
    f3iche_template_exists,
    f3iche_template_path,
    f3iche_template_status,
    infer_broad_f3iche,
    list_f3iche_template_ids,
    resolve_discovery_f3iche_niche,
    resolve_discovery_f3iche_niche_async,
    resolve_discovery_f3iche_niche_with_llm,
)

__all__ = [
    "f3iche_template_exists",
    "f3iche_template_path",
    "f3iche_template_status",
    "infer_broad_f3iche",
    "list_f3iche_template_ids",
    "resolve_discovery_f3iche_niche",
    "resolve_discovery_f3iche_niche_async",
    "resolve_discovery_f3iche_niche_with_llm",
]
