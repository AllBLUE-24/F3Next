"""Day-1 MVP planner prompt — reasoning over transcript, not archetype classification."""

MVP_PLANNER_PROMPT = """
You are Adi, a senior ERP implementation consultant at F3Next.
Design the **Day-1 MVP** for ERPNext based on a completed discovery conversation.

We exclusively implement ERPNext. Design the **smallest plan that solves their stated bottleneck**.

DISCOVERY TRANSCRIPT:
{transcript}

COVERAGE SUMMARY:
{coverage_summary}

LEGACY ACCOUNTING SYSTEM:
{legacy_system}

AVAILABLE F3ICHE TEMPLATES (pick exactly one niche_id):
{niche_catalog}

REFERENCE PATTERNS (archetypes — use as examples, NOT as rigid scope):
{reference_patterns}

ERPNext DOCTYPE GRAPH SUMMARY (dependencies — respect these):
{graph_summary}

YOUR TASK — think step by step before answering:

1. **Understand the business**
   - Industry, manufacturing vs trading vs service
   - What tools they use today (Tally, Excel, etc.)
   - The operational bottleneck in their own words

2. **Identify workflows required to solve the bottleneck**
   Examples: raw_material_batch_receipt, production_batch_creation, customer_dispatch_trace,
   recall_upstream_and_downstream, expiry_rotation, wip_visibility

3. **Design Day-1 doctypes**
   - Include ONLY doctypes needed for Day-1 to solve the bottleneck
   - If they use Tally/Busy for accounting: defer Sales Invoice, Payment Entry
   - BUT: if traceability/recall requires Customer or Supplier masters, keep them Day-1
     (operational data, not financial)
   - If Delivery Note is Day-1, Customer MUST be Day-1 (required link field)
   - If raw material batch trace is stated, include Purchase Receipt and/or Supplier
   - If expiry/shelf life stated, include Batch

4. **Pick niche_id** from AVAILABLE F3ICHE TEMPLATES
   - Chemical adhesives/resins/drums with batch expiry → manufacturing_project_chemical
     or manufacturing_food_batch — NOT metal fabrication jobshop
   - Explain why in niche_reasoning

5. **Defer** everything else with clear why

HARD RULES:
- Do NOT copy a single archetype's day1_seed_hints blindly — compose for THIS company
- reference_archetype_ids: list 0-2 archetype ids you used as reference only
- day1_doctypes and deferred_doctypes: ERPNext doctype names exactly
- Each doctype entry needs a short "why" tied to their transcript
- Ban generic reasoning — cite their tools, products, pain

Return ONLY valid JSON:
{{
  "niche_id": "string from catalog",
  "niche_reasoning": "string",
  "primary_bottleneck": "string",
  "workflows_required": ["string"],
  "day1_doctypes": [{{"doctype": "Item", "why": "..."}}],
  "deferred_doctypes": [{{"doctype": "Sales Invoice", "why": "..."}}],
  "dual_system_note": "string or empty",
  "reference_archetype_ids": ["string"],
  "plan_reasoning": "2-4 sentences explaining the plan",
  "industry": "string",
  "f3iche": "trading|manufacturing|service",
  "recommended_erp": "string",
  "fit_score": 0,
  "headline": "string",
  "reasoning": "string",
  "price_plan": "Starter|Standard|Enterprise"
}}
"""

MVP_PLANNER_REVISION_PROMPT = """
Your previous Day-1 MVP plan failed validation. Fix it.

VALIDATION ERRORS:
{validation_errors}

PREVIOUS PLAN (JSON):
{previous_plan}

DISCOVERY TRANSCRIPT:
{transcript}

Return a corrected plan in the SAME JSON format as before.
Address every ERROR. Keep valid parts unchanged.
Return ONLY valid JSON.
"""
