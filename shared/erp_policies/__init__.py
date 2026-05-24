"""Shared ERPNext policy helpers for IS and OS."""

from shared.erp_policies.action_risk import (
    build_confirmation_preview,
    classify_action_risk,
    requires_confirmation,
)
from shared.erp_policies.lifecycle import (
    get_lifecycle_config,
    should_auto_submit_on_import,
)

__all__ = [
    "build_confirmation_preview",
    "classify_action_risk",
    "get_lifecycle_config",
    "requires_confirmation",
    "should_auto_submit_on_import",
]
