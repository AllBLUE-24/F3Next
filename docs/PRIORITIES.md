# F3Next — Sprint Priorities & Ship Plan

> **Purpose:** Action-oriented priority stack for completing the product for launch.  
> **Last updated:** 2026-05-25  
> **Status:** Active sprint plan — overrides weekly focus until next review.

**Related docs**

- [`PRODUCT_BACKLOG.md`](./PRODUCT_BACKLOG.md) — master queue (streams, idea inbox, done log)
- [`IS_V2_BACKLOG.md`](./IS_V2_BACKLOG.md) — IS detail (P0–P4, golden matrix, anti-patching rules)
- [`ARCH_IMPLEMENTATION.md`](./ARCH_IMPLEMENTATION.md) — current IS pipeline
- [`ARCH_V2_VISION.md`](./ARCH_V2_VISION.md) — long-term agentic direction (not this sprint)

---

## Launch definition (“product complete enough”)

A new company can:

1. **Sign up → onboard → invite a colleague** (multi-user, not a single-user dead end)
2. **Upload messy files → analyze → honest validate → sandbox import** (trust what they see)
3. **Ask the assistant** on Validate what’s wrong with mapping (chat bar v1)
4. **Land on a credible marketing page** in a sales conversation

**Explicitly not required for this milestone:** WhatsApp alerts, proactive Monday bot, full v2 reasoning agent, global theme refresh.

---

## North star (this sprint)

> **Companies onboard once, invite their team, upload messy data, and get a trustworthy ERP implementation** — without consultants or ERP training.

---

## Decision log (2026-05-25)

| Decision | Rationale |
|----------|-----------|
| **Park Green Surface golden re-run** | P0 merge/validation code shipped; blocked on worker deploy + supervisor UX, not corpus model. Re-verify on next clean worker deploy. |
| **Validate honesty before chat bar** | Chat on a lying UI creates confident wrong answers. IS P1 before IS P2 chat. |
| **Platform auth + invite in parallel with IS P1** | Product is multi-user; stepping out of backend-only loop. |
| **WhatsApp / proactive bot → post-launch** | Tier 6 — after core loop is demo-ready. |

---

## Priority tiers (work in this order)

### Tier 0 — Unblock demos (~half day)

Do before the next live upload or customer demo.

| ID | Item | Stream | Status |
|----|------|--------|--------|
| 0a | Rebuild `implementation_worker` (not just restart) | IS | **manual** — run after pull |
| 0b | Validation-time KB defaults + mapping `naming_series` | IS | **done** (2026-05-25) |
| 0c | Supervisor: obsolete open prompts when loop exits | IS | **done** (2026-05-25) |
| 0d | Supervisor auto_fix `apply_kb_defaults` for naming_series | IS | **done** (2026-05-25) |

**Deploy after pull (required for 0a):**

```bash
docker compose build implementation_worker
docker compose up -d implementation_worker
```

Then terminate stale `impl-{project_id}` workflow in Temporal and re-upload, **or** navigate to validate if workflow already past supervisor.

**What shipped in code:**

- `defaults.py` — inject doctype-level `naming_series` at map time + `normalize_mapped_payload()`
- `validation_agent/activities.py` — apply KB defaults before validation; write back to R2
- `is_launcher.py` — validate preview applies defaults when reading R2
- `supervisor_agent` — auto_fix op `apply_kb_defaults`; skip ask_user for naming_series-only gaps
- `workflow.py` — apply auto_fixes before ask_user; obsolete open prompts on loop exit; no orphan prompt on cycle 3
- `persist_supervisor_prompt.py` — `obsolete_supervisor_prompts` activity

---

### Tier 1 — IS trust (2–3 days) — **before chat bar**

Users must trust validate colors, counts, and readiness %.

| ID | Item | Outcome |
|----|------|---------|
| 1a | UI badges: Passed / Passed with warnings / Failed | No green on bad data |
| 1b | Readiness ≠ 100% when warnings exist | Honest session score |
| 1c | Flatten child tables in validate preview | Stock Entry / PR show item_code, qty (not `--`) |
| 1d | Session-level `partial` when any doctype has warnings | Overall status matches reality |

**Defer this sprint:** full `ValidationReport` JSON schema, multi-agent supervisor debate (IS P3).

---

### Tier 2 — Platform: multi-user product (3–5 days)

| ID | Item | Outcome | Paths |
|----|------|---------|-------|
| 2a | Forgot password flow | `/forgot-password` + Supabase `resetPasswordForEmail` | `frontend/src/app/(auth)/login/page.tsx` |
| 2b | Reset password callback page | Email link lands correctly | New route + Supabase redirect config |
| 2c | Onboarding wizard polish | Company, slug, role, industry — less friction | `frontend/src/app/(auth)/onboarding/page.tsx` |
| 2d | Post-onboarding → invite team | No single-user dead end after company create | New step in onboarding |
| 2e | Invite admin: list / send / revoke | Company admin can manage team | API + UI |
| 2f | Invite accept page polish | Premium welcome, mobile-friendly | `[companySlug]/invite/[inviteCode]/page.tsx` |

**Phase B (after 2a–2f work):** login/signup visual redesign, auth email templates, org roles enforcement (Platform P2).

---

### Tier 3 — IS chat bar (3–5 days) — **after Tier 1**

Persistent assistant on Validate (stretch: Analyze).

| ID | Item | Outcome |
|----|------|---------|
| 3a | Chat input on Validate right panel | User describes mapping/validation issues in natural language |
| 3b | Context wiring | Session id, validation errors, doctype summary, open supervisor actions — no hallucinated row counts |
| 3c | Wire to `refine_mapping_with_llm` + supervisor respond | e.g. “map party_name to supplier_name” |
| 3d | (Stretch) Same shell on Analyze | Pre-validate questions |

**Not in chat bar v1:** auto-reclassify file from chat, full NL pipeline control (IS P4).

---

### Tier 4 — Marketing & public face (2–4 days, parallel OK)

Can run alongside Tier 2 if capacity allows.

| ID | Item | Outcome |
|----|------|---------|
| 4a | Landing hero + ICP refresh | Manufacturing / mid-market ERP migration, strong CTA |
| 4b | Section consistency | Comparison, WhyUs, Vision, Contact, PrivateCohort — one grid/typography |
| 4c | Green Surface case study block | Proof point (anonymized or named) |

**Defer:** pricing page, SEO pass, demo video embed (Marketing P3).

---

### Tier 5 — Polish (after Tiers 1–4 demo-ready)

| ID | Item |
|----|------|
| 5a | User profile / company settings pages |
| 5b | Login + signup premium redesign |
| 5c | Implementation shell visual pass (StepRail, Analyze, Sandbox) |
| 5d | Global theme / design tokens — **last** (avoid restyling auth twice) |

---

### Tier 6 — Post-launch / v2 (explicitly last)

| ID | Item | When |
|----|------|------|
| 6a | Personal templates / F3iche playbooks per company | After IS + onboarding stable |
| 6b | WhatsApp / Slack alerts (import done, validate blocked) | After notification infra |
| 6c | Proactive context chatbot (“Monday QC check?”) | Post-launch; see ARCH_V2_VISION |
| 6d | Full v2 reasoning agent (live schema, tool calling) | Not this sprint |

---

## Focus this sprint (max 5)

| # | Item | Tier | Stream | Status |
|---|------|------|--------|--------|
| 1 | IS validate honesty (badges, child preview, readiness) | 1 | IS | pending |
| 2 | Forgot password + reset flow | 2 | Platform | pending |
| 3 | Onboarding → invite team step | 2 | Platform | pending |
| 4 | Chat bar v1 on Validate (input + context + refine_mapping) | 3 | IS | pending |
| 5 | Landing hero refresh | 4 | Marketing | pending |

**Rule:** Do not start #4 until #1 is done. Tier 0 before any customer upload.

---

## Suggested day plan (aggressive)

| Days | Focus |
|------|--------|
| **1–2** | Tier 0 (worker/supervisor) + Tier 1 IS validate UI |
| **2–4** | Tier 2 Platform auth + invite (end-to-end invite flow) |
| **3–5** | Tier 3 Chat bar v1 on Validate |
| **4–6** | Tier 4 Landing pass (parallel with Tier 3 if two tracks) |
| **6+** | Tier 5 polish only if 1–4 are demo-ready |

---

## IS P0 status (parked verification)

Code shipped; live golden run deferred.

| Item | Code | Live verify |
|------|------|-------------|
| Row-level required values | done | deferred |
| Merge quarantine | done | deferred |
| Cross-file merge guard | done | deferred |
| Customer-in-Supplier leak | done | deferred |
| Golden matrix doc | done | — |
| Project classification + naming_series defaults | done in repo | needs worker rebuild + fresh run |
| Green Surface 8-file matrix pass | — | next worker deploy |

Checklist when re-running: [`GREEN_SURFACE_GOLDEN_MATRIX.md`](../containers/implementation/dev_fixtures/GREEN_SURFACE_GOLDEN_MATRIX.md)

---

## Not doing now

- Full golden re-run as a gate for every other task
- Multi-agent supervisor debate
- Global theme refresh (Design P4)
- WhatsApp / proactive operations bot
- v2 live-schema agent replacement for KB
- Export validate PDF, trust score demos

---

## Idea mapping (founder inputs → tiers)

| Idea | Tier | Backlog reference |
|------|------|-------------------|
| Chat bar + NL supervisor on mapping/validate | 3 | IS P2 in [`IS_V2_BACKLOG.md`](./IS_V2_BACKLOG.md) |
| Onboarding, invite, auth, marketing, profiles | 2, 4, 5 | Platform P1–P2, Marketing P2 in [`PRODUCT_BACKLOG.md`](./PRODUCT_BACKLOG.md) |
| Templates, WhatsApp, proactive Monday bot | 6 | Idea inbox → post-launch |

---

## Review cadence

- **Daily:** pick 1–2 items from Focus table; mark done in [`PRODUCT_BACKLOG.md`](./PRODUCT_BACKLOG.md) Done log when shipped.
- **Weekly:** refresh Focus table here + in PRODUCT_BACKLOG; re-rank tiers if launch date moves.

---

## Review log

| Date | Changes |
|------|---------|
| 2026-05-25 | Created sprint plan; parked golden re-run; ordered Tiers 0–6; mapped founder ideas to tiers |
