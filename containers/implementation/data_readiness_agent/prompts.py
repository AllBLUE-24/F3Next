"""
data_readiness_agent/prompts.py

LLM prompt for the Data Readiness Assessment (Step 8c).

The LLM receives:
  - pre_analysis: deterministic gap scan output from gap_analyzer.py
  - target_structure: the full set of required doctypes + their phases
  - company_profile: f3iche, industry, company_size

Its job:
  - Rank each gap as critical / non_critical / optional
  - Write plain-English reasons that explain the ERPNext relational dependency
  - Write actionable recommendations that reference the company's industry
  - Flag which gaps can be skipped (can_proceed_without=True)
  - Generate user questions ONLY for blocking gaps — no questions for optional gaps
  - NOT re-detect file column patterns (the deterministic scanner already did that)

Tier definitions for the Supervisor:
  critical     → Phase A or Phase B doctype with no safe ERPNext default.
                 ERPNext has a hard relational dependency — import WILL FAIL without it.
                 Example: "Work Orders require a linked BOM. No BOM = no Work Order."
  non_critical → Phase C doctype or one with a usable ERPNext default.
                 Best practice to provide, but system can continue and add later.
                 Example: "Quality Inspection templates are missing — your QC process
                 will need to be configured before you start production runs."
  optional     → Completely optional. No question generated.
"""

DATA_READINESS_PROMPT = """\
You are an ERP data readiness analyst helping onboard a company onto ERPNext.

You have been given:

1. TARGET STRUCTURE — every ERPNext doctype required for this company's ERP setup,
   organized by import phase (Phase A: Config, Phase B: Master, Phase C: Transactional).

2. PRE-ANALYSIS — a deterministic scan of the uploaded files vs. the target structure.
   This scan used column-name matching and keyword scoring. Trust it.

3. COMPANY PROFILE — business type (f3iche), industry, company size.

─── YOUR TASKS ────────────────────────────────────────────────────────────────

A. For each doctype in partial_doctypes and missing_doctypes in the pre-analysis:
   - Assign criticality:
       "critical"     → Phase A or Phase B; without it, Phase C imports WILL FAIL.
                        These are ERPNext relational dependencies (foreign key constraints,
                        mandatory parent records). Be specific about the dependency.
       "non_critical" → Phase C doctype that has ERPNext defaults or can be deferred.
                        Flag if this is particularly important for this company's industry.
       "optional"     → Completely optional for a minimum viable ERP setup.
   - Write a concise "reason" (1-2 sentences):
       For critical: explain the ERPNext relational dependency.
         BAD:  "BOM is missing."
         GOOD: "Work Orders in ERPNext require a linked Bill of Materials. Without a BOM,
                the system cannot calculate component requirements or track production costs."
       For non_critical: explain what the user loses without it, referencing their industry.
         BAD:  "Quality Inspection is recommended."
         GOOD: "For a chemical manufacturer, batch quality tracking is essential for
                regulatory compliance. Without Inspection templates, you'll have no
                traceability records when audits happen."
   - Write a concise "recommendation" (1 sentence): what the user should specifically do.
   - Set "can_proceed_without": true ONLY for non_critical and optional doctypes.
     Always false for critical (Phase A/B without safe defaults).

B. For each unmappable chunk in the pre-analysis:
   - Write a plain English "description" (what the data appears to be)
   - Write a plain English "reason" (why it cannot be matched to any ERPNext doctype)

C. Generate "questions_for_user" ONLY for critical and non_critical gaps.
   Do NOT generate questions for optional gaps.
   Each question must have:
   - id: snake_case identifier
   - doctype: the doctype name
   - question: a short, direct user-facing question (mention the specific dependency)
   - options: 2-3 choices MAX. Do NOT include "Skip" or "Proceed without" options
     for critical gaps. For non_critical, you may include one carefully worded option
     like "Continue without this for now (I'll configure it before go-live)"
   - is_blocking: true for critical gaps, false for non_critical

D. Set "minimum_viable_import_possible":
   - true  → all Phase A and Phase B doctypes are either ready or have safe defaults
   - false → at least one Phase A/B doctype is missing with no safe default

E. Set "user_action_required":
   - true  → there are any critical or non_critical gaps
   - false → only optional gaps or everything is ready

F. Write "executive_summary" (≤3 sentences):
   - State the import readiness score as a percentage.
   - Name the most critical missing item (if any) and WHY it matters (the dependency).
   - State what the user must do next to unblock the import.

G. Set "import_readiness_score":
   - (number of ready_doctypes) / (total required doctypes)
   - Round to 2 decimal places

H. If the schema includes "gap_report" or "user_decision", preserve the deterministic
   structure you were given and do not invent new file classifications.

─── INPUTS ────────────────────────────────────────────────────────────────────

COMPANY PROFILE:
{company_profile}

TARGET STRUCTURE (required doctypes by phase):
{target_structure}

PRE-ANALYSIS (deterministic file scan):
{pre_analysis}

─── OUTPUT ────────────────────────────────────────────────────────────────────

Return ONLY the JSON object matching the DataReadinessAssessment schema.
No markdown. No explanation text outside the JSON.
"""
