"""resolve_entities activity (mocked adapter)."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from containers.os.entity_resolution.activities import resolve_entities


def test_resolve_entities_skipped_when_dummy() -> None:
    out = asyncio.run(resolve_entities({
        "intent_dict": {
            "target_doctype": "Sales Order",
            "entities": {"customer": "Acme", "items": [{"item_code": "X", "qty": 1}]},
        },
        "context": {
            "company_profile": {"is_dummy": True},
            "erp_credentials": {},
        },
    }))
    assert out.get("skipped") is True
    assert "link_cache" in out.get("context_overlay", {})


def test_resolve_entities_populates_link_cache() -> None:
    asyncio.run(_resolve_entities_populates_link_cache())


async def _resolve_entities_populates_link_cache() -> None:
    mock_adapter = MagicMock()
    mock_adapter.list_records = AsyncMock(
        side_effect=lambda dt, fields, **kw: [
            {"name": "bauli baramati"} if dt == "Customer" else {"name": "ITEM-1"},
        ]
    )

    with patch("shared.erp_adapters.registry.get_adapter", return_value=mock_adapter):
        from shared.erp_adapters.link_resolver import ResolutionMap

        with patch(
            "containers.os.entity_resolution.activities.build_link_cache",
            new_callable=AsyncMock,
            return_value={"Customer": ["bauli baramati"], "Item": ["ITEM-1"]},
        ), patch(
            "containers.os.entity_resolution.activities.build_resolution_map",
            new_callable=AsyncMock,
            return_value=ResolutionMap(
                resolved={"Customer": {"bauli": "bauli baramati"}},
            ),
        ):
            out = await resolve_entities({
                "intent_dict": {
                    "target_doctype": "Sales Order",
                    "entities": {
                        "customer": "bauli",
                        "items": [{"item_code": "ITEM-1", "qty": 1}],
                    },
                },
                "context": {
                    "company_profile": {"erp_url": "http://x", "api_key": "k", "api_secret": "s"},
                    "erp_credentials": {
                        "erp_url": "http://x",
                        "api_key": "k",
                        "api_secret": "s",
                    },
                    "defaults": {},
                },
            })

    assert out.get("skipped") is False
    overlay = out.get("context_overlay") or {}
    assert "Customer" in overlay.get("link_cache", {})
    intent = out.get("intent_dict") or {}
    assert intent.get("entities", {}).get("customer") in ("bauli baramati", "bauli")
