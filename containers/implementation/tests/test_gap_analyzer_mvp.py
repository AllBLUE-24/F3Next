"""MVP-scoped gap analyzer tests — Green Surface 3rd_run golden fixtures."""
from __future__ import annotations

from containers.implementation.data_readiness_agent.gap_analyzer import analyze_gaps
from containers.implementation.file_io.manifest_utils import build_manifest_v2
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

MVP_SEEDS = [
    "Customer",
    "Supplier",
    "Item",
    "Project",
    "Sales Order",
    "Purchase Order",
]

DEFERRED = ["BOM", "Work Order", "Employee"]


def _target_structure():
    return {
        "seed_doctypes": MVP_SEEDS,
        "deferred_doctypes": DEFERRED,
        "required_doctypes": MVP_SEEDS + ["Company", "Warehouse", "UOM"],
        "setup_steps": [
            {"doctype": dt, "phase": "phase_b_master", "action": "must_create"}
            for dt in ("Customer", "Supplier", "Item")
        ]
        + [
            {"doctype": dt, "phase": "phase_c_transactional", "action": "must_create"}
            for dt in ("Project", "Sales Order", "Purchase Order")
        ],
        "import_phases": {},
    }


def _analyze():
    manifest = build_manifest_v2(THIRD_RUN_FILES, created_at="2026-06-05T00:00:00Z")
    manifest["corpus_understanding"] = {
        "corpus_summary": "Party master, client orders, purchase orders",
        "files": [
            {
                "filename": "messy_partners.csv",
                "likely_erpnext_doctypes": ["Customer", "Supplier"],
            },
            {
                "filename": "client_orders.csv",
                "likely_erpnext_doctypes": ["Sales Order", "Project", "Customer"],
                "explicitly_not_doctypes": ["Work Order", "BOM"],
            },
            {
                "filename": "raw_purchase_orders.csv",
                "likely_erpnext_doctypes": ["Purchase Order", "Supplier", "Item"],
            },
        ],
    }
    return analyze_gaps(manifest, _target_structure(), _kb_field_mappings())


def test_mvp_scope_uses_seed_doctypes_not_full_graph():
    result = _analyze()
    summary = result["summary"]
    assert summary["mvp_scoped"] is True
    assert summary["total_required"] == len(MVP_SEEDS)


def test_party_split_covers_customer_and_supplier():
    result = _analyze()
    ready = {r["doctype"]: r for r in result["ready_doctypes"]}
    missing = [m["doctype"] for m in result["missing_doctypes"]]

    assert "Customer" in ready
    assert "Supplier" in ready
    assert "Customer" not in missing
    assert "Supplier" not in missing
    assert ready["Customer"].get("ready_with_assumptions") is True
    assert ready["Customer"]["source_file"] == "messy_partners.csv"
    assert ready["Supplier"]["source_file"] == "messy_partners.csv"


def test_item_stub_from_transactional_files():
    result = _analyze()
    ready = {r["doctype"]: r for r in result["ready_doctypes"]}
    assert "Item" in ready
    assert ready["Item"].get("ready_with_assumptions") is True
    assert ready["Item"]["source_file"] in ("client_orders.csv", "raw_purchase_orders.csv")


def test_deferred_doctypes_not_scanned():
    result = _analyze()
    all_doctypes = (
        [r["doctype"] for r in result["ready_doctypes"]]
        + [p["doctype"] for p in result["partial_doctypes"]]
        + [m["doctype"] for m in result["missing_doctypes"]]
    )
    for deferred in DEFERRED:
        assert deferred not in all_doctypes


def test_assumptions_emitted_for_defaultable_fields():
    result = _analyze()
    assumptions = result.get("assumptions") or []
    doctypes_with_assumptions = {a["doctype"] for a in assumptions}
    assert "Customer" in doctypes_with_assumptions or "Supplier" in doctypes_with_assumptions


def test_no_blocking_gaps_for_mvp_masters():
    result = _analyze()
    summary = result["summary"]
    assert summary["n_blocking_missing"] == 0
    assert summary["raw_readiness_score"] >= 0.5
