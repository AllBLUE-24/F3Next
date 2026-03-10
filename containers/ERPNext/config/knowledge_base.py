# Static Knowledge Base for ERPNext Inventory Module

# The "Brain" of the Config Agent

ERPNEXT_STOCK_KB_TEXT = """
=== ERPNEXT STOCK MODULE KNOWLEDGE BASE ===

1. VALUATION & COMPLIANCE
   - Rule: Pharma/Food/Chemicals (#Ind_Process_Mfg) MUST use "FIFO" for batch traceability.
   - Rule: Retail/Trading (#Ind_Retail) should use "Moving Average" for margin stability.
   - Rule: If #Comp_Strict_Audit is active, set `allow_negative_stock = 0`.
   - Rule: If #Ind_Retail is active, set `allow_negative_stock = 1` (Speed over accuracy).

2. TRACEABILITY (BATCHES & SERIALS)
   - Rule: #Inv_Batch -> Set `batch_naming_series` to "BATCH-.YYYY.-.####".
   - Rule: #Inv_Serial -> Set `auto_create_serial_no = 1` (Reduces manual entry).
   - Rule: #Inv_Barcode -> Enable `show_barcode_field` AND `scan_barcode_on_mobile`.

3. WAREHOUSE TOPOLOGY (CRITICAL)
   - Rule: #Site_Single -> Create one "Stores - Main".
   - Rule: #Site_Multi -> Create "All Warehouses" (Group) -> Children: "HQ Store", "Branch A", "Branch B".
   - Rule: #Ind_Manufacturing -> ALWAYS create "WIP - Production" and "Scrap" warehouses.

4. RECEIPT & QUALITY
   - Rule: #Mod_Quality -> Enable `enable_quality_inspection` in Buying Settings.
   - Rule: #Ind_Manufacturing -> Enable `allow_over_delivery` (10% tolerance) for raw materials.
   - Rule: #Ind_Retail -> Disable `allow_over_delivery` (Strict unit counting).

5. UNITS OF MEASURE (UOM)
   - Rule: #Inv_MultiUOM -> Set `allow_different_uom = 1`.
   - Rule: "Nos", "Box", "Pack", "Unit" must always have `must_be_whole_number = 1`.
   - Rule: "Kg", "Ltr", "Mtr" must always have `must_be_whole_number = 0` (Decimals allowed).

6. ITEM DEFAULTS
   - Rule: "Raw Material" group should default to "Stores" warehouse.
   - Rule: "Finished Goods" group should default to "Stores" warehouse (unless Multi-Site).

=== NEW LOGIC RULES (STRICT) ===

1. DEFAULTS (ALWAYS APPLY UNLESS OVERRIDDEN):
   - auto_create_serial_and_batch_bundle_for_outward = 1
   - clean_description_html = 1
   - role_allowed_to_over_deliver_receive = "Stock Manager"

2. INFERRED RULES (TAG BASED):
   - IF tag #Ind_Retail IS PRESENT -> Set show_barcode_field = 1.
   - IF tag #Ind_Pharma IS PRESENT -> Set pick_serial_and_batch_based_on = "Expiry".
   - IF tag #Site_Multi IS PRESENT -> Create Warehouse Tree: "All Warehouses" -> ["HQ", "Branch"].
   - IF tag #Site_Single IS PRESENT -> Create Warehouse: "Stores - Main".

3. USER ANSWERS (HIGHEST PRIORITY):
   - IF user selected "FIFO" -> valuation_method = "FIFO".
   - IF user selected "Strict" -> allow_negative_stock = 0.
   - User answers ALWAYS override Tag Defaults.

=== END KNOWLEDGE BASE ===
"""