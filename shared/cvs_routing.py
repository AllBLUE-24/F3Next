"""ERP doctype → CVS layer routing (shared by API, launcher, and workers)."""


def layers_for_doctype(doctype: str) -> list[str]:
    """
    Determine which context layers need rebuilding for a given ERPNext doctype.

    Master data changes (Customer, Item, etc.) → rebuild master_data only.
    Transactional changes (SO, Invoice, etc.)  → rebuild transaction_intel only.
    Unknown → rebuild both (safe fallback).
    """
    MASTER_DATA_DOCTYPES = {
        "Customer",
        "Supplier",
        "Item",
        "Warehouse",
        "Cost Center",
        "Item Group",
        "UOM",
        "Territory",
        "Payment Terms",
        "Price List",
        "Item Price",
    }

    TRANSACTION_DOCTYPES = {
        "Sales Order",
        "Purchase Order",
        "Sales Invoice",
        "Purchase Invoice",
        "Delivery Note",
        "Purchase Receipt",
        "Payment Entry",
        "Stock Entry",
        "Stock Ledger Entry",
        "Journal Entry",
        "Quotation",
        "Material Request",
    }

    if doctype in MASTER_DATA_DOCTYPES:
        return ["master_data"]
    if doctype in TRANSACTION_DOCTYPES:
        return ["transaction_intel"]
    return ["master_data", "transaction_intel"]
