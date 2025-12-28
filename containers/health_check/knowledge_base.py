
KNOWLEDGE_BASE = {
  "industry_benchmarks": {
    "inventory_carrying_cost_percent": 0.18,
    "manual_invoice_processing_cost_inr": 60,
    "average_data_entry_error_rate": 0.04,
    "healthy_inventory_turnover_ratio": 6
  },
  "tangible_assets": [
    {"threshold": 100000, "item": "Three High-End Laptops"},
    {"threshold": 500000, "item": "One Senior Engineer's Salary"},
    {"threshold": 1500000, "item": "A Brand New Hyundai Creta"},
    {"threshold": 3000000, "item": "A New CNC Machine"},
    {"threshold": 10000000, "item": "A New Factory Shed"}
  ],
  "risk_matrix": [
    {
      "id": "R1",
      # Note: 'inventory_tracking' maps to question 'inventory_value' or a derived field in your logic
      "condition_field": "inventory_value", 
      "condition_values": ["I honestly don't know (No live record)"],
      "severity": "CRITICAL",
      "diagnosis": "Inventory Blindness",
      "consequence": "You are likely losing 5-10% of stock to theft and wastage without knowing it.",
      "solution_module": "F3 Store Management (Barcode Enabled)"
    },
    {
      "id": "R2",
      "condition_field": "bom_management",
      "condition_values": ["We have Excel BOMs, but production often changes"],
      "severity": "HIGH",
      "diagnosis": "The Excel Death Spiral",
      "consequence": "Excel cannot handle complex items with live movement. Your stock accuracy is likely below 70%.",
      "solution_module": "F3 Cloud Inventory"
    },
    {
      "id": "R3",
      "condition_field": "costing_method",
      "condition_values": ["Mental Math (Rough estimate based on material)", "Tally (Purchase cost only)"],
      "severity": "HIGH",
      "diagnosis": "Margin Erosion",
      "consequence": "You are selling products based on old raw material prices. You might be making a loss on every unit sold.",
      "solution_module": "F3 Manufacturing (BOM & Costing)"
    },
    {
      "id": "R4",
      "condition_field": "store_manager_dependency",
      "condition_values": ["Disaster. He knows where everything is kept"],
      "severity": "EXISTENTIAL",
      "diagnosis": "Key Person Risk",
      "consequence": "You don't own a business; you own a chaos engine dependent on one person. If they leave, production stops.",
      "solution_module": "F3 Roles & Permissions"
    }
  ],
  "roi_formulas": {
    "dead_capital_interest_rate": 0.12, # 12% OD interest
    "excess_inventory_threshold": 0.15 # 15% of turnover
  }
}