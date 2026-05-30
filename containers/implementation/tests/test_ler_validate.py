"""IS LER on validate/readiness paths (foundation/is-brain)."""

from __future__ import annotations

import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch

from containers.implementation.ler_apply import ler_validate_enabled
from shared.entity_resolution.rows import resolve_rows_for_payload


def test_resolve_rows_for_payload_rewrites_customer() -> None:
    asyncio.run(_resolve_rows_for_payload_rewrites_customer())


async def _resolve_rows_for_payload_rewrites_customer() -> None:
    payload = {
        "records": [{"customer": "acme", "customer_name": "Acme"}],
        "link_fields": {"customer": "Customer"},
    }
    adapter = MagicMock()

    with patch(
        "shared.entity_resolution.rows.build_resolution_map",
        new_callable=AsyncMock,
    ) as mock_build:
        from shared.erp_adapters.link_resolver import ResolutionMap

        mock_build.return_value = ResolutionMap(
            resolved={"Customer": {"acme": "Acme Corp"}},
        )
        updated, summary = await resolve_rows_for_payload(
            adapter,
            payload,
            {"customer": "Customer"},
        )

    assert updated["records"][0]["customer"] == "Acme Corp"
    assert summary.get("corrections") or summary.get("link_targets")


def test_ler_validate_enabled_default_on() -> None:
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("IS_USE_LER_VALIDATE", None)
        assert ler_validate_enabled() is True


def test_ler_validate_enabled_off() -> None:
    with patch.dict(os.environ, {"IS_USE_LER_VALIDATE": "0"}):
        assert ler_validate_enabled() is False


def test_apply_ler_skips_when_disabled() -> None:
    asyncio.run(_apply_ler_skips_when_disabled())


async def _apply_ler_skips_when_disabled() -> None:
    from containers.implementation.ler_apply import apply_ler_to_session_mapped_data

    with patch.dict(os.environ, {"IS_USE_LER_VALIDATE": "0"}):
        report = await apply_ler_to_session_mapped_data(
            project_id="proj-1",
            company_slug="testco",
            mapped_data={"Customer": {"records": []}},
            s3=MagicMock(),
            r2_keys_by_doctype={},
        )
    assert report.get("skipped") is True


def test_assess_live_erp_masters_empty_customer() -> None:
    asyncio.run(_assess_live_erp_masters_empty_customer())


async def _assess_live_erp_masters_empty_customer() -> None:
    from containers.implementation.data_readiness_agent.live_erp import assess_live_erp_masters

    fake_adapter = MagicMock()
    with patch(
        "shared.entity_resolution.is_adapter.resolve_is_erp_adapter",
        new_callable=AsyncMock,
        return_value=("https://erp.test", fake_adapter),
    ), patch(
        "shared.entity_resolution.ler.fetch_link_cache_for_doctypes",
        new_callable=AsyncMock,
        return_value={
            "Customer": [],
            "Supplier": ["S1"],
            "Item": ["I1"],
            "Company": ["C1"],
            "Warehouse": ["W1"],
        },
    ):
        result = await assess_live_erp_masters(
            "proj-1",
            ["Sales Order"],
        )

    assert "Customer" in result["live_empty"]
    assert len(result["complete_gaps"]) >= 1
    assert result["complete_gaps"][0]["severity"] == "blocking"
    assert result["complete_gaps"][0]["rule_id"] == "is_live_erp_empty"


def test_assess_live_erp_skips_without_adapter() -> None:
    asyncio.run(_assess_live_erp_skips_without_adapter())


async def _assess_live_erp_skips_without_adapter() -> None:
    from containers.implementation.data_readiness_agent.live_erp import assess_live_erp_masters

    with patch(
        "shared.entity_resolution.is_adapter.resolve_is_erp_adapter",
        new_callable=AsyncMock,
        return_value=(None, None),
    ):
        result = await assess_live_erp_masters("proj-1", ["Customer"])

    assert result.get("skipped") is True
    assert result["complete_gaps"] == []
