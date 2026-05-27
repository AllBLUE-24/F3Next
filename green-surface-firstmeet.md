# Green Surface — First Beta Session

> **Demo guide** for first early customer (Green Surface).  
> **Planning docs:** [`docs/PRIORITIES.md`](docs/PRIORITIES.md) (tiers + pre-demo day plan) · [`docs/IS_V2_BACKLOG.md`](docs/IS_V2_BACKLOG.md) (10 pillars + universal IS bridge) · [`docs/PRODUCT_BACKLOG.md`](docs/PRODUCT_BACKLOG.md)

---

## What to tell him upfront (2-minute framing)
The honest pitch:

"This is early beta. You can register, deploy your own ERPNext sandbox, upload CSVs, and walk through analyze → validate → import. We've hardened it heavily for manufacturing-style data like yours — items, parties, BOMs, work orders, projects, purchase receipts, stock entries.

It's not 'any ERPNext doctype from any random file' yet. If you upload something we don't have mapping rules for, the system may ignore it or classify it wrong — and we'll learn from that.

If important columns are missing, the system usually catches it — either during data readiness (before mapping), on the validate screen (errors/warnings), or via supervisor questions. It won't always ask in perfect plain English, and sometimes it fills safe defaults silently (customer group, territory, naming series) instead of asking. We want to see which of those moments confuse you."

Supported doctypes today (KB-backed mapping modules):

Item, Customer, Supplier, BOM, Work Order, Project, Purchase Receipt, Stock Entry, plus Sales Order, Sales Invoice, Purchase Order, Payment Entry, Journal Entry, Employee, Batch.

That's ~15 doctypes with real mapping rules — not all 400+ ERPNext doctypes.

Green Surface golden path (what you've rehearsed): 8 files → 8 doctype panels. His own files don't need to match yours exactly, but similar structure works best.

Will missing columns get caught?
Partially yes — here's the real behavior:

Stage	What happens
Data readiness (Analyze, before mapping)
Scans uploaded files vs target doctypes. Critical gaps (e.g. no items before BOMs) → supervisor questions with "Upload missing data" / "Provide defaults". Can proceed without some Phase C gaps.
Mapping
Applies KB defaults for many fields (customer_group, territory, supplier_type, company on Project, naming_series, dates). Silent fill — user may not know.
Validate
Checks required field columns → hard errors (Missing required field: transaction_date). Checks empty values in rows → errors or partial. Warnings for sparse data, enum mismatches (naming_series).
Supervisor on validate
Can ask about missing required fields with an LLM-written message — but only when supervisor is enabled and gaps are detected at that layer.
What won't work perfectly yet:

Sidebar may still show 100% readiness even with warnings (known P1 bug — pre-mapping assessment, not post-mapping truth).
Green "Passed" badges can appear when there are amber warnings underneath.
Child table columns (PR line items, Stock Entry items) may show -- in preview even when data exists (folded, not flattened in UI yet).
A wrong filename (e.g. projects.csv classified as Purchase Receipt) may not always get a clear "did you mean Project?" prompt.
Re-upload / re-import on same sandbox can duplicate docs unless he starts fresh (idempotency improved but not bulletproof for all doctypes).
Purchase Receipt & Stock Entry import as Draft by design — he submits manually in ERPNext.
So: missing supplier_name or item_code → likely caught. Missing posting_date on a transactional doc → error or warning. Missing optional-ish fields → often defaulted without asking.

UI quirks — tell him, fix later
Acknowledge these so he doesn't think he's doing something wrong:

Approve mapping / Confirm F3iche / Validate buttons may still appear briefly (or on refresh) even after clicking — stage polling lag or local UI state. Refreshing Validate can reset the "confirmed" step.
Analyze sidebar "100% / Ready: 11" is a pre-mapping assessment — not live validate truth.
Onboarding + landing page are functional, not polished — Tier 2/4 in backlog.
Don't apologize endlessly; frame as "known beta UI debt — tell us what felt broken."

Pre-demo checklist (you, before he touches anything)
Ops (do today morning)

 Push feature/is-link-resolution-v2 (commit a9cbc1b or later) and rebuild worker on DO:
docker compose build implementation_worker
docker compose up -d implementation_worker

 Confirm frontend + backend on prod/staging match that branch.

 Smoke test yourself once: register → onboard → deploy → upload 1–2 Green Surface files → reach Validate.

 Have Temporal UI open — you'll want it when workflows stall.

 Have worker logs tail ready: docker compose logs -f implementation_worker

 Decide: fresh ERPNext sandbox for him vs shared — recommend his own deploy so duplicates don't confuse.

 Prepare a shared doc (Notion/Google Doc) titled "Green Surface Beta — Session Log" with columns: Step | What he did | What system showed | Expected? | Notes.
What to give him

 App URL, login instructions

 Optional: your 8-file corpus as reference, not requirement — "start with 2–3 files if you want, or make your own"

 ERPNext sandbox URL pattern (shows after deploy ready)

 Your WhatsApp/Slack for "stuck" pings during beta week

 Explicit: "Break it. Wrong files, missing columns, weird names — that's the point."
What NOT to do demo day

 Don't merge Phase 2 / SchemaResolver untested

 Don't promise chat bar on Validate (Tier 3, not built)

 Don't promise WhatsApp alerts / proactive bot
His journey — step-by-step with watch points
Register / Login
Onboarding
Deploy ERPNext
Upload CSVs
Analyze + F3iche confirm
Data readiness prompts
Mapping + Approve
Validate
Import
ERPNext sandbox
Step	He does	You watch for	Learning goal
Register
Email signup
Supabase auth, redirect
Auth friction
Onboarding
Company name, slug, role
Slug collision, form clarity
Onboarding UX (Tier 2c)
Deploy
Trigger deploy, wait
Stuck at deploying %, timeout
Infra reliability
Upload
Drag CSVs
File size, encoding, multi-file
Upload UX
F3iche confirm
Pick business type
Wrong niche inference
Profile quality
Data readiness
Answer/skip gaps
Questions too vague or too many
Supervisor copy quality
Mapping approve
Click approve
Button still visible, long wait
Stage polling bug
Validate
Review panels, badges
Wrong doctype, row counts, -- columns
Trust / honesty gaps
Import
Confirm import
Link errors, duplicates, draft PR/SE
ERP graph + idempotency
Sandbox
Open ERPNext
Records exist, BOM submitted, PR draft
End-to-end value
Failure-learning script (intentionally try these)
Pick 3–5 during the session; don't do all at once.

Easy wins (system should handle):

Upload items + parties only → readiness should flag missing BOM before WO.
CSV with empty supplier names on some rows → validate should fail/partial on Supplier.
Rename file sensibly (gs_items.csv, suppliers.csv) → classification should work.
Medium (interesting failures): 4. Missing date column on work orders → error or default date injected — note which. 5. One file, mixed customers + suppliers without clear column → party split behavior. 6. Upload a 7th random file (e.g. employees) → maps if KB exists; else "extra" or ignored.

Hard (expect rough edges): 7. Terrible filename (data.csv, sheet1.csv) → wrong doctype classification. 8. Re-run import without clearing sandbox → duplicate BOMs/WOs (document behavior). 9. Skip a critical data readiness question → does import fail later with a clear message?

For each: don't rescue immediately. Ask: "What did you expect?" → log it.

During the demo — your role
You're facilitator + logger, not hero fixer.

First 15 min: Let him drive register → deploy with minimal hand-holding.
When stuck >3 min: note where, then help — but capture the stuck state first (screenshot + stage from network tab or Temporal).
After Validate: walk panels together — row counts, source files, amber vs green. Ask: "Would you trust this enough to click Import?"
After Import: open ERPNext together — 2 BOMs not 4, 2 WOs not 6, PR in Draft.
Close: 10-min retro — top 3 confusing moments, top 1 thing that felt magic.
What to log (template)
Session: GS-beta-001 | Date | His sandbox URL | Temporal workflow ID
| # | Step | Input | System response | Pass/Fail/Confusing | Fix tier |
|---|------|-------|-----------------|---------------------|----------|
| 1 | Upload | items.csv, no BOM | Readiness asked for BOM? | | P0/P1/UI |
| 2 | Validate | missing posting_date | Error text exact wording | | |
Tag fixes: P0 (wrong data in ERP), P1 (UI lies), UI (button stuck), UX (copy confusing).

One-liners for common questions
"Can I upload anything?"
→ "CSV/Excel-style tabular data for the doctypes we support. Invoices, inventory, BOMs, parties — yes. Random PDFs or niche modules — not yet."

"What if my columns have different names?"
→ "We match common synonyms (party_name → supplier/customer). Weird names may map wrong — tell us."

"Why is Purchase Receipt Draft?"
→ "By policy we don't auto-submit stock docs; you review in ERPNext first."

"Why 100% ready but warnings on Validate?"
→ "Known bug — sidebar is pre-mapping score. Trust the validate panels, not the sidebar %."

"Button didn't disappear after I approved"
→ "Known — refresh or ignore if next step loaded. We're fixing button state."

After demo (your backlog, not his problem)
Priority order from your docs:

Tier 1 — validate honesty (badges, readiness %, child table preview)
UI button state — hide confirm cards after stage advances; persist Validate confirmed step
Post-mapping readiness recheck — sidebar should reflect validate reality
Tier 2/4 — onboarding + landing polish (when you have bandwidth)
Bottom line
Yes: For KB-covered doctypes, any reasonable rows in those doctypes can work — not just your golden 8 files. Column mapping + defaults + validate catch a lot.

No: It's not "any doctype, any schema, always asks nicely." Defaults hide gaps; UI can lie in places; classification can mis-route badly named files.

Demo success = he completes one full loop or hits 3–5 memorable failures you fully understand — both are wins for early beta.

If you want, I can turn the session log table into a copy-paste Notion template, or a minimal "beta tester README" paragraph you can send him before the call. (Ask mode — I can't create the file unless you switch to Agent mode.)