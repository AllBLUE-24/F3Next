"""Discovery target structure and MVP boundary generation."""
from containers.discovery.target.build_target import (
    build_discovery_target,
    build_post_discovery_target,
)
from containers.discovery.target.persist import generate_project_target_structure

__all__ = [
    "build_discovery_target",
    "build_post_discovery_target",
    "generate_project_target_structure",
]
