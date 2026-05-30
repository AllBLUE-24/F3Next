"""
Golden matrix ID → unit test anchors (v1.0.0 RELEASE_v1_0_0.md).

These tests document which automated tests cover which golden rows.
They do not replace manual E2E on pilot tenants.
"""

from __future__ import annotations

import importlib

# golden_id -> pytest module(s) that must import cleanly
GOLDEN_UNIT_ANCHORS: dict[str, list[str]] = {
    "G-OS-PO-02": ["shared.tests.test_kb_policy"],
    "G-OS-CO-01": ["containers.os.tests.test_validator_company_guard"],
    "G-OS-VAL-01": ["containers.os.tests.test_workflow_gates"],
    "G-OS-PO-01": ["containers.os.tests.test_business_fields"],
    "G-OS-MERGE-01": ["containers.os.tests.test_business_fields"],
    "G-IS-READ-01": ["containers.implementation.tests.test_live_erp_readiness"],
    "G-IS-LER-01": ["containers.implementation.tests.test_ler_validate"],
    "G-IS-VAL-01": ["shared.tests.test_validation_kb_rules"],
    "G-IS-IMP-01": [],  # frontend vitest — see import-results.test.ts
    "E1": ["shared.tests.test_kb_policy"],
    "E2": ["containers.os.tests.test_business_fields"],
    "E3": ["containers.os.tests.test_business_fields"],
    "B2": ["containers.os.tests.test_validator_company_guard"],
}


def test_golden_matrix_modules_importable() -> None:
    missing: list[str] = []
    for golden_id, modules in GOLDEN_UNIT_ANCHORS.items():
        for mod in modules:
            try:
                importlib.import_module(mod)
            except Exception as exc:
                missing.append(f"{golden_id}: {mod} ({exc})")
    assert not missing, "Golden anchor imports failed:\n" + "\n".join(missing)


def test_golden_matrix_has_core_os_is_coverage() -> None:
    required = {
        "G-OS-PO-02",
        "G-OS-CO-01",
        "G-IS-READ-01",
        "G-IS-LER-01",
    }
    assert required.issubset(GOLDEN_UNIT_ANCHORS.keys())
