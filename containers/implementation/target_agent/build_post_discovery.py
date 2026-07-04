"""Backward-compatible re-exports — canonical module is containers.discovery.target.build_target."""
from containers.discovery.target.build_target import (
    build_discovery_target,
    build_post_discovery_target,
)

__all__ = ["build_discovery_target", "build_post_discovery_target"]
