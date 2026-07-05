# Research Handoff — Discovery Archetype Catalog

Engineering consumes archetypes **only** through `containers/discovery/archetype_registry.py`.  
You do **not** need to notify us per id for scoping to work — but run validation before merge.

## Validate before merge

```bash
python -m containers.discovery.kb.validate_archetypes
```

Fix all **errors**; warnings (hints not on a F3iche template) are OK if doctype exists in ERPNext graph.

## Required fields per archetype

```json
{
  "archetype_id": "snake_case_unique_id",
  "primary_bottleneck": "Plain-language pain label",
  "signals": ["words", "phrases", "user might say"],
  "functional_requirements": ["capability_phrase_snake_case"],
  "day1_seed_hints": ["Item", "BOM", "Stock Entry"],
  "defer_typically": ["Payroll"],
  "notes": "Compliance, dual-system, defer rationale"
}
```

## Where to put rows

| Scope | File |
|-------|------|
| Cross-sector / most niches | `containers/discovery/kb/archetype_catalog.json` |
| Niche-specific override (same id replaces catalog row) | `containers/knowledge_base/common/f3iches/<niche>.json` → `bottlenecks[]` |

## Sector grouping (optional, recommended)

Add to catalog `_meta.sectors` as Research organizes bulk adds:

```json
"_meta": {
  "sectors": {
    "Manufacturing & Job Work": [
      "subcontractor_job_work_yield_leakage",
      "machine_downtime_logging"
    ],
    "Trading & Distribution": ["procurement_gap"]
  }
}
```

Ids must still appear in `archetypes[]` with full blocks. Sectors are for LLM prompt grouping only.

## Priority ids blocking golden tests

Please land these **before** the bulk 30–50 if possible:

| Priority | `archetype_id` (proposed) | Day-1 seeds must include |
|----------|---------------------------|---------------------------|
| P0 | `custom_order_pipeline` | Quotation, Sales Order, Project |
| P0 | `incoming_quality_compliance` | Quality Inspection, Quality Inspection Template, Batch |
| P1 | `quality_hold_quarantine` | Quality Inspection, Stock Entry, Batch |

## Questions for Research to confirm

1. Final id for custom order / quote-to-order CRM? (`custom_order_pipeline` ok?)
2. Final id for ISO / incoming raw material QC? (not `scrap_wastage`)
3. Will sector names in `_meta.sectors` be stable for docs?
4. Any archetype ids in chemical F3iche that should move to catalog-only?

## Current id inventory (do not rename without engineering note)

**Chemical F3iche:** `inventory_visibility`, `basic_costing`, `factory_wip_bridge`, `scrap_wastage`, `distributor_ship_and_debit_margin_blindness`, `landed_cost_allocation_blindness`, `multi_currency_exchange_volatility`, `subcontractor_retainage_and_ra_billing`

**Global catalog:** `basic_inventory`, `excel_bom_disconnect`, `procurement_gap`, `invoicing_receivables`, `service_dispatch_chaos`, `subcontractor_job_work_yield_leakage`, `warranty_rma_and_reverse_logistics_chaos`, `multi_tier_sales_commission_and_payable_desynchronization`, `eway_bill_transit_and_compliance_hazard`

New ids: pick new snake_case names; do not collide unless F3iche intentionally overrides.
