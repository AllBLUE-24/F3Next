import unittest
from unittest.mock import AsyncMock, MagicMock

from shared.erp_adapters.import_idempotency import (
    build_idempotency_filters,
    find_existing_record,
    pick_best_existing,
)


class ImportIdempotencyTest(unittest.TestCase):
    def test_bom_filters_by_item_and_company(self) -> None:
        filters = build_idempotency_filters(
            "BOM",
            {"item": "FG-PRIMER-A", "company": "Green Surface"},
        )
        self.assertEqual(
            filters,
            [["item", "=", "FG-PRIMER-A"], ["company", "=", "Green Surface"]],
        )

    def test_work_order_filters_require_bom_no(self) -> None:
        filters = build_idempotency_filters(
            "Work Order",
            {"production_item": "FG-PRIMER-A"},
        )
        self.assertIsNone(filters)

        filters = build_idempotency_filters(
            "Work Order",
            {"production_item": "FG-PRIMER-A", "bom_no": "BOM-FG-PRIMER-A-001"},
        )
        self.assertEqual(
            filters,
            [
                ["production_item", "=", "FG-PRIMER-A"],
                ["bom_no", "=", "BOM-FG-PRIMER-A-001"],
            ],
        )

    def test_pick_best_existing_prefers_submitted_bom(self) -> None:
        picked = pick_best_existing(
            [
                {"name": "BOM-A-002", "docstatus": 0, "is_default": 1},
                {"name": "BOM-A-001", "docstatus": 1, "is_default": 1},
            ],
            prefer_submitted=True,
            prefer_default=True,
        )
        self.assertEqual(picked["name"], "BOM-A-001")

    def test_supplier_uses_dedupe_key_fallback(self) -> None:
        filters = build_idempotency_filters(
            "Supplier",
            {"supplier_name": "Apex Chemicals Ltd."},
        )
        self.assertEqual(filters, [["supplier_name", "=", "Apex Chemicals Ltd."]])


class FindExistingRecordAsyncTest(unittest.IsolatedAsyncioTestCase):
    async def test_find_existing_work_order(self) -> None:
        adapter = MagicMock()
        adapter.list_records = AsyncMock(
            return_value=[{"name": "MFG-WO-2026-00001", "docstatus": 0}]
        )
        row = {
            "production_item": "FG-PRIMER-A",
            "bom_no": "BOM-FG-PRIMER-A-001",
        }
        found = await find_existing_record(adapter, "Work Order", row)
        self.assertEqual(found["name"], "MFG-WO-2026-00001")
        adapter.list_records.assert_awaited_once()

    async def test_work_order_fallback_to_production_item_only(self) -> None:
        adapter = MagicMock()
        adapter.list_records = AsyncMock(
            side_effect=[
                [],
                [{"name": "WO-00001", "docstatus": 0, "production_item": "FG-PRIMER-A"}],
            ]
        )
        row = {
            "production_item": "FG-PRIMER-A",
            "bom_no": "BOM-MISSING",
        }
        found = await find_existing_record(adapter, "Work Order", row)
        self.assertEqual(found["name"], "WO-00001")
        self.assertEqual(adapter.list_records.await_count, 2)


if __name__ == "__main__":
    unittest.main()
