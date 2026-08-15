"""Generate test scenarios from F3iche archetypes or live sessions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .schemas import (
    CompanyContext,
    CorpusFileStub,
    ExpectedMVP,
    GapResponseTemplate,
    TestScenario,
)


def load_f3iche_kb(archetype: str) -> dict[str, Any]:
    """Load F3iche KB file for archetype.
    
    Args:
        archetype: F3iche path (e.g., "manufacturing/project/chemical")
    
    Returns:
        KB JSON data
    """
    kb_path = Path("shared/kb/f3iche") / f"{archetype}.json"
    if not kb_path.exists():
        raise FileNotFoundError(f"F3iche KB not found: {kb_path}")
    
    with open(kb_path) as f:
        return json.load(f)


def infer_mvp_from_pain(pain: str, kb: dict[str, Any]) -> ExpectedMVP:
    """Infer expected MVP boundary from pain point and KB policies.
    
    Args:
        pain: Pain point description (e.g., "WIP visibility")
        kb: F3iche KB data
    
    Returns:
        Expected MVP structure
    
    Note:
        This is a simplified heuristic. Real discovery uses LLM + graph traversal.
        For test scenarios, we manually define expected MVPs per pain pattern.
    """
    # Common pain pattern → seed doctype mappings
    pain_lower = pain.lower()
    
    seed_doctypes = []
    
    if "wip" in pain_lower or "work in progress" in pain_lower:
        seed_doctypes = ["Work Order", "BOM", "Item"]
    elif "stock" in pain_lower or "inventory" in pain_lower:
        seed_doctypes = ["Stock Entry", "Item", "Warehouse"]
    elif "sales" in pain_lower or "order" in pain_lower:
        seed_doctypes = ["Sales Order", "Item", "Customer"]
    elif "purchase" in pain_lower or "procurement" in pain_lower:
        seed_doctypes = ["Purchase Order", "Item", "Supplier"]
    elif "scheduling" in pain_lower or "capacity" in pain_lower:
        seed_doctypes = ["Work Order", "Workstation", "Item"]
    else:
        # Generic manufacturing baseline
        seed_doctypes = ["Item", "BOM", "Work Order"]
    
    # Add always_ask_doctypes from KB
    always_ask = kb.get("always_ask_doctypes", [])
    for dt in always_ask:
        if dt not in seed_doctypes:
            seed_doctypes.append(dt)
    
    # Deferred doctypes
    deferred_doctypes = kb.get("defer_doctypes_until_post_mvp", [])
    
    # Simplified dependency graph
    dependency_graph = {
        "Work Order": ["BOM", "Item"],
        "BOM": ["Item"],
        "Sales Order": ["Item", "Customer"],
        "Purchase Order": ["Item", "Supplier"],
        "Stock Entry": ["Item", "Warehouse"],
    }
    
    return ExpectedMVP(
        seed_doctypes=seed_doctypes,
        deferred_doctypes=deferred_doctypes,
        dependency_graph=dependency_graph,
    )


def generate_corpus_stubs(seed_doctypes: list[str]) -> list[CorpusFileStub]:
    """Generate corpus file stubs for seed doctypes.
    
    Args:
        seed_doctypes: List of required doctypes
    
    Returns:
        Corpus file stubs for simulated user to generate
    """
    # Doctype → typical filename mappings
    filename_map = {
        "Item": "items.csv",
        "BOM": "bom.xlsx",
        "Work Order": "work_orders.csv",
        "Sales Order": "sales_orders.csv",
        "Purchase Order": "purchase_orders.csv",
        "Customer": "customers.csv",
        "Supplier": "suppliers.csv",
        "Warehouse": "warehouses.csv",
        "Workstation": "workstations.csv",
        "Stock Entry": "stock_entries.csv",
    }
    
    # Doctype → required columns (simplified)
    required_columns_map = {
        "Item": ["item_code", "item_name", "stock_uom"],
        "BOM": ["item", "quantity"],
        "Work Order": ["production_item", "qty", "wip_warehouse"],
        "Sales Order": ["customer", "delivery_date"],
        "Purchase Order": ["supplier", "schedule_date"],
        "Customer": ["customer_name"],
        "Supplier": ["supplier_name"],
        "Warehouse": ["warehouse_name"],
        "Workstation": ["workstation_name"],
        "Stock Entry": ["item_code", "qty", "s_warehouse", "t_warehouse"],
    }
    
    stubs = []
    for doctype in seed_doctypes:
        filename = filename_map.get(doctype, f"{doctype.lower().replace(' ', '_')}.csv")
        required_columns = required_columns_map.get(doctype, ["name"])
        
        stubs.append(
            CorpusFileStub(
                filename=filename,
                expected_doctype=doctype,
                required_columns=required_columns,
                sample_row_count=10,
                field_coverage_percent=80.0,
            )
        )
    
    return stubs


def compute_expected_gaps(
    mvp: ExpectedMVP, corpus_files: list[CorpusFileStub]
) -> list[str]:
    """Compute expected data gaps from MVP and corpus files.
    
    Args:
        mvp: Expected MVP boundary
        corpus_files: Corpus file stubs
    
    Returns:
        List of expected gap field names
    
    Note:
        This is a placeholder. Real gap computation requires doctype metadata
        and field-level analysis. For tests, we manually define expected gaps.
    """
    # For simplicity, assume 20% of fields will have gaps
    # (since corpus_files have field_coverage_percent=80.0)
    expected_gaps = []
    
    for stub in corpus_files:
        if stub.expected_doctype == "Work Order":
            expected_gaps.extend([
                "Work Order.bom_no",
                "Work Order.planned_start_date",
            ])
        elif stub.expected_doctype == "Item":
            expected_gaps.extend([
                "Item.item_group",
                "Item.default_warehouse",
            ])
    
    return expected_gaps


def generate_gap_responses(expected_gaps: list[str]) -> list[GapResponseTemplate]:
    """Generate gap response templates for expected gaps.
    
    Args:
        expected_gaps: List of expected gap fields (format: "Doctype.field")
    
    Returns:
        Gap response templates
    """
    responses = []
    
    for gap in expected_gaps:
        if "." in gap:
            doctype, field = gap.split(".", 1)
        else:
            doctype, field = "Unknown", gap
        
        # Default strategy: provide a dummy value for MVP, defer complex fields
        if field in ["bom_no", "item_group", "warehouse"]:
            responses.append(
                GapResponseTemplate(
                    gap_field=field,
                    doctype=doctype,
                    response_type="provide_value",
                    value="Default",
                )
            )
        else:
            responses.append(
                GapResponseTemplate(
                    gap_field=field,
                    doctype=doctype,
                    response_type="defer",
                )
            )
    
    return responses


def generate_scenario(
    name: str,
    f3iche: str,
    pain: str,
    company_name: str = "Test Manufacturing Co",
    industry: str = "Manufacturing",
) -> TestScenario:
    """Generate a complete test scenario.
    
    Args:
        name: Unique scenario name (kebab-case)
        f3iche: F3iche archetype (e.g., "manufacturing/project/chemical")
        pain: Pain point description
        company_name: Company name (default test name)
        industry: Industry sector
    
    Returns:
        Complete TestScenario
    """
    # Load KB
    kb = load_f3iche_kb(f3iche)
    
    # Infer MVP
    expected_mvp = infer_mvp_from_pain(pain, kb)
    
    # Generate corpus stubs
    corpus_files = generate_corpus_stubs(expected_mvp.seed_doctypes)
    
    # Compute gaps
    expected_gaps = compute_expected_gaps(expected_mvp, corpus_files)
    
    # Generate gap responses
    gap_responses = generate_gap_responses(expected_gaps)
    
    # Expected record counts (1 per seed doctype for simplicity)
    expected_record_counts = {dt: 10 for dt in expected_mvp.seed_doctypes}
    
    return TestScenario(
        name=name,
        description=f"Test {f3iche} implementation for {pain}",
        context=CompanyContext(
            name=company_name,
            industry=industry,
            size="small",
            f3iche=f3iche,
        ),
        pain_point=pain,
        expected_mvp=expected_mvp,
        corpus_files=corpus_files,
        gap_responses=gap_responses,
        expected_validation_issues=[],
        expected_record_counts=expected_record_counts,
    )


def save_scenario(scenario: TestScenario, output_dir: Path) -> Path:
    """Save scenario to JSON file.
    
    Args:
        scenario: TestScenario to save
        output_dir: Directory to save to (e.g., .skills/test-harness/examples/)
    
    Returns:
        Path to saved file
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{scenario.name}.json"
    
    with open(output_path, "w") as f:
        json.dump(scenario.model_dump(), f, indent=2)
    
    return output_path


def load_scenario(name: str, scenarios_dir: Path) -> TestScenario:
    """Load scenario from JSON file.
    
    Args:
        name: Scenario name (without .json extension)
        scenarios_dir: Directory containing scenarios
    
    Returns:
        Loaded TestScenario
    """
    scenario_path = scenarios_dir / f"{name}.json"
    if not scenario_path.exists():
        raise FileNotFoundError(f"Scenario not found: {scenario_path}")
    
    with open(scenario_path) as f:
        data = json.load(f)
    
    return TestScenario(**data)
