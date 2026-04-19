"""
Local test for Mapping Agent — validates fixes against vindhya-spices input data.
OFFLINE-ONLY: No LLM calls. Tests pure logic: split validation, keyword fallback, synonym scoring.

Usage: python containers/implementation/test_mapping_vindhya.py
"""
import csv
import io
import json
import sys
import types
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

# Monkey-patch temporalio for local testing
_mock_activity = types.ModuleType("temporalio.activity")
_mock_logger = types.SimpleNamespace(
    info=lambda *a, **kw: None,
    warning=lambda *a, **kw: None,
    error=lambda *a, **kw: None,
)
_mock_activity.logger = _mock_logger
_mock_activity.defn = lambda **kw: lambda fn: fn
sys.modules["temporalio.activity"] = _mock_activity
sys.modules["temporalio"] = types.ModuleType("temporalio")

# Mock out DB/LLM imports that get pulled in at module level
_mock_db = types.ModuleType("shared.database.db")
_mock_db.AsyncSessionLocal = None
sys.modules["shared"] = types.ModuleType("shared")
sys.modules["shared.database"] = types.ModuleType("shared.database")
sys.modules["shared.database.db"] = _mock_db

# Full mock for IS models
_mock_is_models = types.ModuleType("shared.models.is_models")
for cls_name in ["ISFieldMapping", "ISMappedData", "ISFieldMappingHistory", "ISFile",
                  "ISSession", "ISF3icheScore", "ISCompanyProfile", "ISTargetStructure"]:
    setattr(_mock_is_models, cls_name, type(cls_name, (), {}))
sys.modules["shared.models"] = types.ModuleType("shared.models")
sys.modules["shared.models.is_models"] = _mock_is_models

# Mock sqlalchemy
import sqlalchemy as _real_sa
if not hasattr(_real_sa, 'select'):
    _real_sa.select = lambda *a, **kw: None
    _real_sa.update = lambda *a, **kw: None
    _real_sa.delete = lambda *a, **kw: None

# Mock the LLM helper to just raise (simulating quota exhaustion)
_mock_llm_helper = types.ModuleType("containers.implementation.utils.llm_helper")
def _mock_generate_json(*args, **kwargs):
    raise Exception("MOCK: LLM quota exhausted")
_mock_llm_helper.generate_json = _mock_generate_json
sys.modules["containers.implementation.utils.llm_helper"] = _mock_llm_helper

# Now import the engine
from containers.implementation.mapping_agent.activities import _MappingEngine

INPUTS_DIR = project_root / "attachments" / "vindhya-spices" / "inputs"


def read_file(name: str) -> str:
    with open(INPUTS_DIR / name, "r", encoding="utf-8") as f:
        return f.read()


def test_employee_infer_doctype():
    """employee_list.csv columns should score highest for Employee doctype."""
    engine = _MappingEngine()
    columns = ["Emp ID", "Full Name", "Department", "Designation", "Date of Joining"]
    doctype = engine.infer_doctype(columns)
    assert doctype == "Employee", f"Expected Employee, got {doctype}"
    print(f"  ✅ Employee columns → infer_doctype → Employee")


def test_inventory_infer_doctype():
    """inventory_data.csv columns should score highest for Item doctype (with new synonyms)."""
    engine = _MappingEngine()
    columns = ["Item Code", "Item Name", "Type", "UOM", "Cost Rate (INR)", "Selling Rate (INR)", "Stock Qty"]
    doctype = engine.infer_doctype(columns)
    assert doctype == "Item", f"Expected Item, got {doctype}"
    print(f"  ✅ Inventory columns → infer_doctype → Item")


def test_inventory_no_split():
    """_split_by_entity_type should NOT split inventory_data.csv (Type=Raw Material etc.)."""
    engine = _MappingEngine()
    content = read_file("inventory_data.csv")
    rows = list(csv.DictReader(io.StringIO(content)))
    clean_rows = [{k: v for k, v in r.items() if k is not None} for r in rows]
    columns = list(clean_rows[0].keys())
    
    result = engine._split_by_entity_type(clean_rows, columns)
    assert result is None, f"Should NOT split inventory by Type. Got: {list(result.keys()) if result else 'None'}"
    print(f"  ✅ inventory _split_by_entity_type → None (correctly skipped)")
    

def test_parties_split():
    """_split_by_entity_type should split parties_directory.csv into Supplier + Customer."""
    engine = _MappingEngine()
    content = read_file("parties_directory.csv")
    rows = list(csv.DictReader(io.StringIO(content)))
    clean_rows = [{k: v for k, v in r.items() if k is not None} for r in rows]
    columns = list(clean_rows[0].keys())
    
    result = engine._split_by_entity_type(clean_rows, columns)
    assert result is not None, "Should split parties_directory.csv"
    assert "Supplier" in result, f"Missing Supplier group. Got: {list(result.keys())}"
    assert "Customer" in result, f"Missing Customer group. Got: {list(result.keys())}"
    
    supplier_names = [r["Entity Name"] for r in result["Supplier"]]
    customer_names = [r["Entity Name"] for r in result["Customer"]]
    
    assert len(result["Supplier"]) == 2, f"Expected 2 suppliers, got {len(result['Supplier'])}: {supplier_names}"
    assert len(result["Customer"]) == 3, f"Expected 3 customers, got {len(result['Customer'])}: {customer_names}"
    
    assert "Kisan Agro Farms" in supplier_names, f"Missing Kisan Agro from Suppliers: {supplier_names}"
    assert "Reliance Smart Bazaar" in customer_names, f"Missing Reliance from Customers: {customer_names}"
    
    print(f"  ✅ parties _split_by_entity_type → Supplier({supplier_names}) + Customer({customer_names})")


def test_parties_doctype_assignment():
    """After splitting, each entity group should get the CORRECT doctype via direct match."""
    engine = _MappingEngine()
    data = engine._load_field_mappings()
    
    # Simulate: entity_type="Customer" should match "Customer" doctype directly
    for entity_type in ["Customer", "Supplier"]:
        matched = None
        for dt_name in data.get("doctypes", {}).keys():
            if entity_type.lower() == dt_name.lower():
                matched = dt_name
                break
        assert matched == entity_type, f"Entity type '{entity_type}' should directly match doctype '{entity_type}', got '{matched}'"
    
    print(f"  ✅ Direct entity-to-doctype matching: Customer → Customer, Supplier → Supplier")


def test_founder_notes_keyword():
    """Keyword fallback should detect Company doctype from founder_notes.txt."""
    engine = _MappingEngine()
    content = read_file("founder_notes.txt")
    doctype = engine._keyword_infer_doctype(content)
    assert doctype == "Company", f"Expected Company, got {doctype}"
    print(f"  ✅ founder_notes.txt keyword → Company")


def test_employee_field_mapping():
    """Employee column mapping should map all key fields."""
    engine = _MappingEngine()
    columns = ["Emp ID", "Full Name", "Department", "Designation", "Date of Joining"]
    mapping = engine.map_columns(columns, "Employee")
    
    assert mapping.get("Full Name") == "employee_name", f"Full Name → {mapping.get('Full Name')}"
    assert mapping.get("Emp ID") == "employee", f"Emp ID → {mapping.get('Emp ID')}"
    assert mapping.get("Department") == "department", f"Department → {mapping.get('Department')}"
    assert mapping.get("Designation") == "designation", f"Designation → {mapping.get('Designation')}"
    assert mapping.get("Date of Joining") == "date_of_joining", f"Date of Joining → {mapping.get('Date of Joining')}"
    
    print(f"  ✅ Employee column mapping: {mapping}")


def test_item_field_mapping():
    """Item column mapping should map key fields with new synonyms."""
    engine = _MappingEngine()
    columns = ["Item Code", "Item Name", "Type", "UOM", "Cost Rate (INR)", "Selling Rate (INR)", "Stock Qty"]
    mapping = engine.map_columns(columns, "Item")
    
    assert mapping.get("Item Code") == "item_code", f"Item Code → {mapping.get('Item Code')}"
    assert mapping.get("Item Name") == "item_name", f"Item Name → {mapping.get('Item Name')}"
    assert mapping.get("UOM") == "stock_uom", f"UOM → {mapping.get('UOM')}"
    
    print(f"  ✅ Item column mapping: {mapping}")


if __name__ == "__main__":
    print("\n═══ Mapping Agent Tests — OFFLINE (No LLM) ═══\n")
    
    tests = [
        ("Employee Doctype Inference", test_employee_infer_doctype),
        ("Inventory Doctype Inference", test_inventory_infer_doctype),
        ("Inventory No Split", test_inventory_no_split),
        ("Parties Split", test_parties_split),
        ("Parties Doctype Assignment", test_parties_doctype_assignment),
        ("Founder Notes Keyword", test_founder_notes_keyword),
        ("Employee Field Mapping", test_employee_field_mapping),
        ("Item Field Mapping", test_item_field_mapping),
    ]
    
    passed = 0
    failed = 0
    
    for name, fn in tests:
        try:
            fn()
            passed += 1
        except Exception as e:
            print(f"  ❌ {name}: {e}")
            failed += 1
    
    print(f"\n═══ Results: {passed} passed, {failed} failed ═══\n")
    sys.exit(1 if failed else 0)
