"""
seed_business_bottlenecks.py

Seeds the pgvector 'business_bottlenecks' collection with agnostic enterprise bottlenecks.
These chunks decouple the Discovery phase from ERP-specific doctypes, outputting 
generic functional requirements which are later translated by the Target Agent.
"""
import os
import sys
import asyncio

# Ensure paths are correct
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from shared.kb_utils import seed_company_context

BOTTLENECK_CHUNKS = [
    {
        "id": "bottleneck_subcontracting",
        "content": """# Bottleneck: The Outsourcing Black Hole
Companies struggling with subcontractor material loss and reconciliation during outsourced manufacturing often lack a unified tracking mechanism. When raw materials are sent out for external processing, inventory valuations become disjointed if the vendor's consumption isn't strictly mathematically linked to the received finished goods, leading to hidden cost leakages, untraceable scrap, and blind spots in the perpetual inventory ledger.

```json
{
  "mvp_focus": {
    "primary_bottleneck": "Subcontractor material loss and reconciliation",
    "functional_requirements": ["subcontracting", "inventory_tracking", "procurement", "bill_of_materials"]
  }
}
```"""
    },
    {
        "id": "bottleneck_traceability_expiry",
        "content": """# Bottleneck: High-Velocity Traceability Failures
High-velocity fulfillment centers often face catastrophic data integrity issues when attempting to trace expiring perishable goods or electronics across hundreds of daily shipments. Relying on legacy text-based tracking creates database bloat, prevents strict First-In-First-Out algorithmic enforcement, and ultimately causes expired goods to accidentally ship to customers, resulting in massive compliance failures and product recalls.

```json
{
  "mvp_focus": {
    "primary_bottleneck": "Traceability and expiry management failures",
    "functional_requirements": ["batch_tracking", "serial_number_tracking", "warehouse_management", "quality_control"]
  }
}
```"""
    },
    {
        "id": "bottleneck_demand_planning",
        "content": """# Bottleneck: Disconnected Long-Term Demand Planning
Manufacturers relying on basic spreadsheets for procurement often experience devastating stockouts or massive capital tied up in excess inventory. When long-term customer delivery schedules and speculative sales forecasts are not mathematically integrated with actual factory lead times, procurement teams are left guessing, resulting in rushed raw material orders, exorbitant expedited shipping fees, and chronic production delays.

```json
{
  "mvp_focus": {
    "primary_bottleneck": "Disconnected demand planning and material shortages",
    "functional_requirements": ["material_requirements_planning", "demand_forecasting", "production_scheduling", "supply_chain_management"]
  }
}
```"""
    },
    {
        "id": "bottleneck_regulatory_capa",
        "content": """# Bottleneck: Regulatory Compliance and CAPA Breakdowns
Organizations lacking a systemic approach to regulatory compliance frequently fail external audits because they cannot logically connect isolated shop floor defects to structural process improvements. When a batch of raw materials fails tolerance testing, the inability to immediately quarantine the goods and automatically trigger a formal corrective and preventive action workflow exposes the enterprise to severe legal liabilities and degraded brand reputation.

```json
{
  "mvp_focus": {
    "primary_bottleneck": "Regulatory compliance and quality assurance failures",
    "functional_requirements": ["quality_management_system", "corrective_and_preventive_actions", "compliance_tracking", "inspection_management"]
  }
}
```"""
    },
    {
        "id": "bottleneck_freight_import_valuation",
        "content": """# Bottleneck: Distorted Freight and Import Valuation
Businesses heavily reliant on international procurement frequently suffer from completely inaccurate gross margin calculations due to delayed freight, customs, and insurance billing. If the system merely values inventory at the raw supplier invoice price and fails to retrospectively distribute massive shipping overheads across the actual physical stock ledger, financial controllers are left with vastly inflated profit reports and distorted physical asset valuations.

```json
{
  "mvp_focus": {
    "primary_bottleneck": "Inaccurate inventory valuation from hidden import costs",
    "functional_requirements": ["landed_cost_management", "inventory_valuation", "multi_currency_accounting", "accounts_payable"]
  }
}
```"""
    },
    {
        "id": "bottleneck_unenforced_contracts",
        "content": """# Bottleneck: Hemorrhaging Capital on Unenforced Vendor Contracts
Procurement departments negotiating long-term, high-volume contracts often lose millions in potential savings due to decentralized purchasing habits. When individual buyers place ad-hoc orders without system-enforced visibility into pre-negotiated, locked-rate corporate agreements, the business bleeds cash by overpaying for commodities while simultaneously failing to hit the minimum contractual volume thresholds required to maintain their favorable vendor tier.

```json
{
  "mvp_focus": {
    "primary_bottleneck": "Unenforced vendor contracts and rogue purchasing",
    "functional_requirements": ["blanket_orders", "vendor_management", "procurement_approval_workflows", "spend_analytics"]
  }
}
```"""
    },
    {
        "id": "bottleneck_siloed_sales_funnel",
        "content": """# Bottleneck: The Siloed Marketing & Sales Funnel
B2B sales organizations often suffer from a severe disconnect between marketing expenditure and actual closed revenue. When preliminary lead generation channels, automated outreach sequences, and active pipeline stages are siloed across disconnected platforms, executives cannot mathematically trace a closed contract back to its originating marketing initiative, making it impossible to calculate true return on investment or identify exactly where prospects are falling out of the funnel.

```json
{
  "mvp_focus": {
    "primary_bottleneck": "Disconnected sales pipeline and untraceable marketing ROI",
    "functional_requirements": ["customer_relationship_management", "lead_tracking", "campaign_management", "sales_forecasting"]
  }
}
```"""
    },
    {
        "id": "bottleneck_multicurrency_ledger",
        "content": """# Bottleneck: Multi-Currency Ledger Desynchronization
Global enterprises operating across multiple sovereign jurisdictions frequently face catastrophic ledger imbalances during fiscal closing. When a centralized system fails to strictly mandate a fixed accounting currency for foreign vendors, or when transactional write-offs and advance payments are manually calculated outside the system without relying on real-time automated exchange rate fetching, historical financial audits become mathematically compromised, leading to severe tax compliance failures.

```json
{
  "mvp_focus": {
    "primary_bottleneck": "Multi-currency ledger imbalances and audit failures",
    "functional_requirements": ["multi_currency_accounting", "exchange_rate_automation", "general_ledger_management", "financial_consolidation"]
  }
}
```"""
    },
    {
        "id": "bottleneck_multilevel_subassembly",
        "content": """# Bottleneck: Uncoordinated Multi-Level Subassembly Production
Manufacturers producing complex machinery often struggle with orchestrating multi-level subassemblies across different factory floors. Without a unified production plan that recursively explodes bills of materials down to the base components, production managers cannot identify shared intermediate components, leading to redundant manufacturing runs, misaligned staging times, and massive bottlenecks at the final assembly station.

```json
{
  "mvp_focus": {
    "primary_bottleneck": "Inefficient subassembly routing and component staging",
    "functional_requirements": ["advanced_manufacturing", "multi_level_bom", "shop_floor_control", "capacity_planning"]
  }
}
```"""
    },
    {
        "id": "bottleneck_inflexible_pricing",
        "content": """# Bottleneck: Inflexible Customer Pricing and Discount Leakage
Wholesale distributors dealing with complex B2B hierarchies frequently lose margin due to rigid pricing systems and unmonitored discount leakage. When sales representatives manually calculate volume discounts or territory-specific promotional pricing instead of relying on an algorithmic pricing engine, the organization suffers from inconsistent customer billing, unapproved price overrides, and the inability to enforce strict credit limits prior to fulfillment.

```json
{
  "mvp_focus": {
    "primary_bottleneck": "Inconsistent B2B pricing and unauthorized discount leakage",
    "functional_requirements": ["pricing_engine", "discount_management", "credit_control", "order_management"]
  }
}
```"""
    },
    {
        "id": "bottleneck_unprofitable_projects",
        "content": """# Bottleneck: Unprofitable Project and Timesheet Bleed
Service providers, IT firms, and construction companies often suffer from massive profit leakage because they cannot tie granular employee timesheets and ad-hoc subcontractor expenses directly to a master project budget. When labor and material costs are not continuously matched against project milestones and billing schedules, the company only discovers a project was unprofitable months after completion.

```json
{
  "mvp_focus": {
    "primary_bottleneck": "Unprofitable projects and disconnected timesheet costing",
    "functional_requirements": ["project_management", "timesheet_tracking", "project_costing", "expense_management"]
  }
}
```"""
    },
    {
        "id": "bottleneck_unexpected_downtime",
        "content": """# Bottleneck: Unexpected Equipment Downtime and Maintenance
Asset-heavy manufacturing and logistics operations frequently experience catastrophic production bottlenecks due to unforeseen equipment failures. Without a systemic preventive maintenance schedule that links spare parts procurement to machine lifecycle data, facilities suffer from extended downtime, expensive emergency repairs, and constantly missed delivery dates.

```json
{
  "mvp_focus": {
    "primary_bottleneck": "Unexpected equipment downtime and reactive maintenance",
    "functional_requirements": ["enterprise_asset_management", "preventive_maintenance", "work_order_management", "downtime_tracking"]
  }
}
```"""
    },
    {
        "id": "bottleneck_omnichannel_desync",
        "content": """# Bottleneck: Omnichannel Retail and E-commerce Inventory Desync
Retailers operating both physical storefronts and online marketplaces frequently damage customer trust by overselling products that are out of stock. When Point-of-Sale terminals do not instantly deduct inventory from a unified ledger connected to platforms like Shopify or Amazon, the business is forced into manual order cancellations, refund processing overhead, and negative seller ratings.

```json
{
  "mvp_focus": {
    "primary_bottleneck": "Omnichannel overselling and inventory desynchronization",
    "functional_requirements": ["omnichannel_retail", "point_of_sale", "e_commerce_integration", "real_time_inventory_sync"]
  }
}
```"""
    }
]

async def seed_all_bottlenecks():
    print(f"Seeding {len(BOTTLENECK_CHUNKS)} agnostic bottlenecks into pgvector...")
    texts = [chunk["content"] for chunk in BOTTLENECK_CHUNKS]
    ids = [chunk["id"] for chunk in BOTTLENECK_CHUNKS]
    
    # We use 'business_bottlenecks' as the collection name to emphasize it is ERP-agnostic
    await seed_company_context(
        texts=texts,
        metadata_list=[{"type": "bottleneck", "id": _id} for _id in ids],
        collection_name="business_bottlenecks"
    )
    print("✅ Bottleneck seeding complete.")

if __name__ == "__main__":
    asyncio.run(seed_all_bottlenecks())
