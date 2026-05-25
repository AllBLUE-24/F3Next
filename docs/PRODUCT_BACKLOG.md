# F3Next — Product Backlog & Weekly Priorities

> **Master queue** for the whole product: IS, Platform, Marketing, Design.  
> **Last reviewed:** 2026-05-25  
> **Review cadence:** ~weekly (update **Focus this week** first)

**Related docs**

- [`IS_V2_BACKLOG.md`](./IS_V2_BACKLOG.md) — detailed IS appendix (P0–P4, golden run, known issues)
- [`ARCH_IMPLEMENTATION.md`](./ARCH_IMPLEMENTATION.md) — IS architecture
- [`ARCH_V2_VISION.md`](./ARCH_V2_VISION.md) — long-term agentic direction

---

## How to use this file

### Add an idea (copy this)

```markdown
- [ ] **Title** — one-line outcome
  - Stream: IS | Platform | Marketing | Design
  - Priority: P0 | P1 | P2 | P3 | P4
  - Added: YYYY-MM-DD
  - Notes: (optional — file paths, links, constraints)
```

### Weekly review (~every 7 days)

1. Update **Focus this week** (max 5 items, any stream).
2. Move completed items to **Done log** (date + one-line note).
3. Re-rank stream P0–P1 if launch or golden-run needs changed.
4. Add one row to **Review log**.
5. Promote ideas from **Idea inbox** or demote to P4.

**Rules**

- **Focus this week** is the only section that overrides stream order.
- Max **5** focus items per week.
- Include at least **1** non-IS item when Platform/Marketing debt exists.
- IS deep work: use [`IS_V2_BACKLOG.md`](./IS_V2_BACKLOG.md) for checklists and anti-patching rules.
- Theme / global rebrand: **Design stream, P4** — after Platform auth/onboarding polish (avoid restyling twice).

---

## Focus this week (reviewed: 2026-05-25)

| # | Item | Stream | Status |
|---|------|--------|--------|
| 1 | Row-level validation + merge quarantine (Green Surface blockers) | IS | pending |
| 2 | Forgot password + reset password flow (Supabase) | Platform | pending |
| 3 | Onboarding → invite team step after company setup | Platform | pending |
| 4 | Validate UI honesty (warnings ≠ green Passed; readiness ≠ 100%) | IS | pending |
| 5 | Landing page refresh (after IS trust fixes) | Marketing | pending |

---

## North star (product)

> **Companies onboard once, invite their team, upload messy data, and get a trustworthy ERP implementation** — without consultants or training.

**IS north star** (implementation detail): see [`IS_V2_BACKLOG.md`](./IS_V2_BACKLOG.md).

---

## Priority legend (product-wide)

| Tier | Meaning | Ship when |
|------|---------|-----------|
| **P0** | Blocker — wrong data, broken auth, or golden run fails | This week |
| **P1** | Trust / completeness — users cannot rely on what they see | Next 1–2 weeks |
| **P2** | UX polish — premium feel, speed, clarity | Scheduled sprint |
| **P3** | Architecture / scale — reduces future patching | When P0–P1 clear |
| **P4** | Later / experiments — theme, nice-to-have | Backlog |

---

## Streams overview

| Stream | P0 | Detail doc | Primary surfaces |
|--------|----|------------|------------------|
| **IS** | 6 | [`IS_V2_BACKLOG.md`](./IS_V2_BACKLOG.md) | Upload → Validate → Sandbox pipeline |
| **Platform** | 0 | (this file) | Auth, onboarding, invites, org/roles |
| **Marketing** | 0 | (this file) | Landing, public pages, cohort |
| **Design** | 0 | (this file) | Theme, tokens — **later phase** |

---

## Stream: IS (Implementation System)

Summary only — full lists, golden checklist, and known issues live in **[`IS_V2_BACKLOG.md`](./IS_V2_BACKLOG.md)**.

### P0 — Blockers (summary)

- [ ] Row-level required **values** (empty `supplier_name`, etc.)
- [ ] Merge quarantine (no `__anon_*` junk rows)
- [ ] Cross-file merge guard (`active_projects` ≠ Purchase Receipt)
- [ ] Project classification confirmed on fresh session + worker restart
- [ ] Green Surface 8-file harness matrix
- [ ] Customer rows leaking into Supplier payload

### P1 — Quality & trust (summary)

- [ ] Sparse data / warnings affect status (`partial`, not 100% readiness)
- [ ] Validate preview: flatten child tables (Stock Entry, PR)
- [ ] Amber “Passed with warnings” badge
- [ ] Structured `ValidationReport` + supervisor on validate

### P2 — IS UX (summary)

- [ ] Chat bar on Validate right panel (+ supervisor / refine mapping)
- [ ] Classification transparency per file
- [ ] Import plan summary on Validate

---

## Stream: Platform (auth, onboarding, teams)

### P1 — Trust & completeness

- [ ] **Forgot password page** — `/forgot-password` using Supabase `resetPasswordForEmail`; link from login.
  - Added: 2026-05-25
  - Notes: [`frontend/src/app/(auth)/login/page.tsx`](../frontend/src/app/(auth)/login/page.tsx) — no forgot link today.

- [ ] **Reset password page** — `/reset-password` (or `/auth/reset`) for email link callback; match Supabase redirect config.
  - Added: 2026-05-25

- [ ] **Onboarding: company-first wizard** — mature multi-step flow (company name, slug, role, industry hint); reduce friction vs single long form.
  - Added: 2026-05-25
  - Notes: [`frontend/src/app/(auth)/onboarding/page.tsx`](../frontend/src/app/(auth)/onboarding/page.tsx)

- [ ] **Post-onboarding: invite team** — after company created, prompt to invite colleagues (email + role); don’t leave single-user dead end.
  - Added: 2026-05-25

- [ ] **Invite admin: send / revoke / list** — company admin can manage pending invites (API + UI).
  - Added: 2026-05-25
  - Notes: accept flow exists at [`frontend/src/app/[companySlug]/invite/[inviteCode]/page.tsx`](../frontend/src/app/[companySlug]/invite/[inviteCode]/page.tsx)

- [ ] **Org roles UX** — who can start IS, validate, approve import, manage invites (document + enforce in UI).
  - Added: 2026-05-25

### P2 — Premium auth & invite UX

- [ ] **Login page redesign** — industry-standard split layout, social proof, subtle motion; parity with Stripe/Linear/Notion quality bar.
  - Added: 2026-05-25
  - Notes: [`frontend/src/app/(auth)/login/page.tsx`](../frontend/src/app/(auth)/login/page.tsx)

- [ ] **Signup page redesign** — visual match to login; clear path to onboarding vs login.
  - Added: 2026-05-25
  - Notes: [`frontend/src/app/(auth)/signup/page.tsx`](../frontend/src/app/(auth)/signup/page.tsx)

- [ ] **Invite accept page polish** — premium welcome, company branding, mobile-friendly; clear CTA for new vs existing users.
  - Added: 2026-05-25
  - Notes: [`frontend/src/app/[companySlug]/invite/[inviteCode]/page.tsx`](../frontend/src/app/[companySlug]/invite/[inviteCode]/page.tsx)

- [ ] **Auth email templates** — reset password, invite, confirm: on-brand HTML (Supabase templates or custom SMTP).

- [ ] **Session / redirect polish** — preserve `redirect` through forgot-password and invite flows.

### P3 — Platform scale

- [ ] SSO / Google OAuth (if needed for enterprise pilots).
- [ ] Audit log for org actions (invites, import approvals).
- [ ] Multi-company user (one login, switch workspace).

---

## Stream: Marketing (landing & public pages)

### P2 — Premium public face

- [ ] **Landing hero refresh** — sharper ICP (manufacturing / mid-market ERP migration), stronger CTA, proof points.
  - Added: 2026-05-25
  - Notes: [`frontend/src/app/(marketing)/landing/page.tsx`](../frontend/src/app/(marketing)/landing/page.tsx), `components/landing/*`

- [ ] **Green Surface case study block** — real implementation story (anonymized or named) on landing.

- [ ] **Marketing section consistency** — Comparison, WhyUs, Vision, Contact, PrivateCohort: shared layout grid, typography, spacing.
  - Notes: [`components/landing/Comparison.tsx`](../frontend/src/components/landing/Comparison.tsx), etc.

- [ ] **Private cohort / early access** — clearer value prop and follow-up UX after signup.
  - Notes: [`components/landing/PrivateCohort.tsx`](../frontend/src/components/landing/PrivateCohort.tsx)

### P3 — Expand marketing surface

- [ ] **Pricing page** (even if “contact us” for now).
- [ ] **Security / trust page** — data handling, R2, Supabase, ERP credentials.
- [ ] **Product tour / demo video** embed on landing.
- [ ] **SEO + metadata** pass on all public routes.

---

## Stream: Design (later phase)

> **Do not start global theme until Platform P1–P2 auth/onboarding ship** — avoids restyling login twice.

### P4 — Theme & design system

- [ ] **Global theme refresh** — color tokens, typography scale, light/dark strategy.
- [ ] **Design tokens file** — shared across marketing + app shell.
- [ ] **Auth + marketing visual unification** — one premium look from landing → login → onboarding.
- [ ] **Implementation shell visual pass** — Validate, Analyze, Sandbox, StepRail (after IS P1 trust fixes).
- [ ] **OS command center visual pass** — [`frontend/src/components/OS/`](../frontend/src/components/OS/)

---

## Idea inbox (unprioritized)

_Promote to a stream + P-tier on weekly review._

- IS chat bar on Upload step (“here’s my vendor list and BOMs in one zip”).
- Export validate report as PDF for customer sign-off.
- Diff view: previous upload wave vs current merged corpus.
- “Trust score” per doctype 0–100 for sales demo.
- WhatsApp / Slack notify when import phase completes.
- Public changelog page fed from Done log.

---

## Done log (product-wide)

| Date | Item | Stream | Notes |
|------|------|--------|-------|
| 2026-05-25 | Product backlog doc created | — | Master queue + weekly format |
| 2026-05-25 | IS merge-on-write, modular KB, validate merge | IS | See IS appendix Done table |

_For IS-only completions, see also [`IS_V2_BACKLOG.md` Done section](./IS_V2_BACKLOG.md#done-recent)._

---

## Review log

| Date | Reviewer | Changes |
|------|----------|---------|
| 2026-05-25 | Product planning | Created master backlog; seeded Platform/Marketing/Design; initial weekly focus |
| 2026-05-25 | IS golden run | IS appendix created (Green Surface gaps) |
