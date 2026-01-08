# The Rigid JSON Structure the AI must fill
# This forces the AI to speak "ERPNext Language"

TARGET_STRUCTURE_JSON = """
{
  "doctype_update": {
    "doctype": "Stock Settings",
    "settings": {
      "item_naming_by": "String (Naming Series / Item Code)",
      "valuation_method": "String (FIFO / Moving Average)",
      "allow_negative_stock": "Int (0/1)",
      "enable_stock_reservation": "Int (0/1)",
      "show_barcode_field": "Int (0/1)",
      "auto_create_serial_and_batch_bundle_for_outward": "Int (1)",
      "clean_description_html": "Int (1)"
    }
  },
  "infrastructure_create": [
    { 
      "doctype": "Warehouse", 
      "warehouse_name": "String", 
      "is_group": "Int (0/1)", 
      "parent_warehouse": "String (Optional)" 
    }
  ]
}
"""