# Green Surface — 8-file golden run matrix

Reference corpus: `attachments/green-surface/greensurface_golden_data/` (+ `2nd_run/`).

| # | File | Expected doctype(s) | Expected rows (deduped) | Phase |
|---|------|---------------------|-------------------------|-------|
| 1 | `01_gs_master_items.csv` | Item | 6 | B |
| 2 | `02_gs_parties.csv` | Customer + Supplier (split) | 2 + 2 | B |
| 3 | `03_gs_bom_recipes.csv` | BOM | 2 (FG parents) | B |
| 4 | `04_gs_factory_work_orders.csv` | Work Order | 2 | C |
| 5 | `05_gs_active_projects.csv` | Project | 2 | D |
| 6 | `2nd_run/suppliers_list.csv` | Supplier (merge) | +4 → **6 total** Supplier | B |
| 7 | `2nd_run/purchase_receipts.csv` | Purchase Receipt | 3 | C |
| 8 | `2nd_run/stock_entries.csv` | Stock Entry | 2 | C |

## Pass criteria (validate screen)

- One panel per **doctype** (not per file); merged `source_files` listed.
- No `active_projects` under Purchase Receipt.
- Supplier panel: **6** named rows, no empty `supplier_name`.
- Customer panel: **2** rows from parties file.
- Project panel: **2** rows.
- Validation **fail** or **partial** if empty identity fields remain (post P0).

## Pass criteria (import)

- Phases B → D complete on Green Surface sandbox without link errors.
- BOM submitted before Work Order (Pass 2.6).

## Re-run checklist

1. Restart IS worker after KB/merge changes.
2. Fresh session — do not reuse R2 from pre-fix runs.
3. Upload all 8 files in one wave.
4. Compare validate UI to matrix above.
