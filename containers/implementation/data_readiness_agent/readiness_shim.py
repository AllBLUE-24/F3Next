"""Backward-compat re-exports for Step 3 readiness (import from readiness package)."""
from containers.implementation.readiness.assess import assess_readiness
from containers.implementation.readiness.matrix import build_readiness_matrix
from containers.implementation.readiness.schema import resolve_required_fields

__all__ = ["assess_readiness", "build_readiness_matrix", "resolve_required_fields"]
