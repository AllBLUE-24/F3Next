"""Factory for ERP adapters."""

from __future__ import annotations

from typing import Any

from shared.erp_adapters.base import ERPAdapter
from shared.erp_adapters.erpnext import ERPNextAdapter


def get_adapter(profile: dict[str, Any]) -> ERPAdapter:
    erp_type = (profile.get("erp_type") or "erpnext").lower()
    if erp_type == "erpnext":
        return ERPNextAdapter(profile)
    raise ValueError(f"Unsupported erp_type: {erp_type}")
