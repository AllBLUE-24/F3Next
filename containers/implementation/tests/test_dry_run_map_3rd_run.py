"""Dry-run mapping golden tests — Green Surface 3rd_run fixtures."""
from __future__ import annotations

from containers.implementation.mapping_agent.dry_run_map import dry_run_map_file
from containers.implementation.mapping_agent.kb import field_mappings as _kb_field_mappings

THIRD_RUN_FILES = {
    "messy_partners.csv": (
        "Company_Name,Role,City,Contact\r\n"
        "Rohan Construction,Customer,Mumbai,Rohan\r\n"
        "Gupta Chemical Traders,Supplier,Ahmedabad,S.K. Gupta\r\n"
        "Ultra Floors Pvt Ltd,Customer,Pune,\r\n"
        "Karan Acids & Solvents,Vendor,Nagpur,Karan"
    ),
    "client_orders.csv": (
        "Client,Project,Target_Date,Product,Vol,Price\r\n"
        "Rohan Construction,PRJ-Mumbai-Mall,2026-08-15,SRV-INSTALL,12000,\r\n"
        "New Age Builders,PRJ-Pune-ITPark,2026-09-01,FG-PRIMER-A,200,52.00"
    ),
    "raw_purchase_orders.csv": (
        "PO_Number,Vendor_Name,Item,Ordered_Qty,Price_Per_Unit\r\n"
        "PO-26-001,Gupta Chemical Traders,RM-EPOX-LIQ,2000,4.60\r\n"
        "PO-26-002,Karan Acids & Solvents,RM-SOLVENT-X,400,\r\n"
        "PO-26-003,Unknown Supplier Ltd,RM-HARD-AMN,100,9.00"
    ),
}


def test_dry_run_customer_from_party_split():
    kb = _kb_field_mappings()
    result = dry_run_map_file(
        THIRD_RUN_FILES["messy_partners.csv"],
        "Customer",
        kb=kb,
    )
    assert result["passed"] is True
    assert result["record_count"] == 2
    assert "customer_name" in result["field_mapping"].values()


def test_dry_run_supplier_from_party_split():
    kb = _kb_field_mappings()
    result = dry_run_map_file(
        THIRD_RUN_FILES["messy_partners.csv"],
        "Supplier",
        kb=kb,
    )
    assert result["passed"] is True
    assert result["record_count"] == 2
    assert "supplier_name" in result["field_mapping"].values()


def test_dry_run_sales_order_with_line_items():
    kb = _kb_field_mappings()
    result = dry_run_map_file(
        THIRD_RUN_FILES["client_orders.csv"],
        "Sales Order",
        kb=kb,
        company_context={"company_name": "Green Surface"},
    )
    assert result["passed"] is True
    assert result["record_count"] == 2
    assert "items" not in (result.get("preflight") or {}).get("missing_fields", [])


def test_dry_run_purchase_order_with_line_items():
    kb = _kb_field_mappings()
    result = dry_run_map_file(
        THIRD_RUN_FILES["raw_purchase_orders.csv"],
        "Purchase Order",
        kb=kb,
        company_context={"company_name": "Green Surface"},
    )
    assert result["passed"] is True
    assert result["record_count"] == 3
    mapped_targets = set(result["field_mapping"].values())
    assert "supplier" in mapped_targets or "supplier_name" in mapped_targets
    assert any(t.startswith("items.") or t == "item_code" for t in mapped_targets)
