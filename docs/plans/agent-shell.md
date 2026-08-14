# North Star — Agent Shell RFC

> **Status:** RFC — target UI for IS and OS  
> **Layer:** L5 (Observability UX) + L1 (Honesty)  
> **IS pillar:** 8 (Gap/supervisor), 9 (Validation trust)  
> **Related:** [`NORTH_STAR.md`](./NORTH_STAR.md) · [`PRESENTATION_AGENT_CONTRACT.md`](./PRESENTATION_AGENT_CONTRACT.md) · [`GOLDEN_MATRIX_MANIFEST.md`](./GOLDEN_MATRIX_MANIFEST.md)

---

## 1. Problem statement

Today’s Implementation UI mirrors **every Temporal signal** as a separate surface:

- Routes: Upload → Analyze → Validate → Import  
- Components: StepRail, BrainVisualizer, Profile teaser, green CTA bars, `SupervisorPanel`, `PromptCard`, `ChatMessageList`, synthesized readiness cards, gap_blocking system messages, quality_gate rows  
- Result: users see **four truths at once** (readiness %, mapping blocked, “ready for validate”, workflow waiting on `validation_submitted`)

OS is closer to the right model (one command stream, inline clarification). IS should feel the same.

---

## 2. Design reference

**Primary reference:** Cursor / Antigravity / Codex — one workspace, not a wizard.

| Cursor pattern | F3Next mapping |
|----------------|----------------|
| Left sidebar (files, tree) | **Session tree** — IS steps or OS history; project context |
| Center editor (main work) | **Agent stream** — messages, inline gates, chat input always on |
| Right panel (plan, diff, file) | **Context drawer** — mapped CSV preview, validate table, import plan |
| `+` / attach | **Upload affordance** — adds files to corpus; no dedicated Upload page |
| Inline apply / reject | **MCQ chips** — one active gate at a time |

---

## 3. Layout contract

```text
┌──────────────────────────────────────────────────────────────────────────┐
│  Top bar: project name · deployment pill · mode toggle (IS | OS)        │
├────────────┬─────────────────────────────────────────┬───────────────────┤
│  Sidebar   │  Agent stream (flex-1)                  │  Drawer (optional) │
│  240px     │                                         │  360–480px         │
│            │  [Gate banner — single, sticky top]      │                   │
│  Tree:     │  ─────────────────────────────────────  │  Tabs:             │
│  · Upload  │  Message history (scroll)               │  · Files           │
│  · Analyze │    · assistant (presentation agent)    │  · Mapped preview  │
│  · Validate│    · user                                │  · Validate        │
│  · Import  │    · inline MCQ (when gate active)     │  · Import plan     │
│  · OS cmd  │  ─────────────────────────────────────  │  · OS plan         │
│            │  Composer: [+] [textarea] [Send]        │                   │
│  Status    │  (never disabled during background poll) │  Closes like      │
│  dot per   │                                         │  Cursor panel      │
│  tree node │                                         │                   │
└────────────┴─────────────────────────────────────────┴───────────────────┘
```

### 3.1 Sidebar

- **IS mode:** linear tree reflecting pipeline phases — not separate apps.  
- **Node states:** `idle` | `running` | `needs_you` | `done` | `warning`.  
- **Exactly one** `needs_you` at a time (honesty).  
- Clicking **Validate** opens drawer to mapped preview; does not navigate away from stream.

### 3.2 Agent stream (main)

- **Single scroll timeline** — no duplicate PromptCard + chat message for same gate.  
- **Gate banner** (sticky): one line — e.g. “Confirm mappings” / “Review validation” / “Upload stock movements”.  
- **Inline gate renderer** (below banner when active):
  - `mcq` — 2–4 chips + optional “Other…”  
  - `upload` — dropzone inline (or `+` opens file picker)  
  - `confirm` — primary / secondary  
  - `open_drawer` — “Review mapped data →”  
- **Free chat** always available — routes to presentation agent + tools; does not replace structured gate.

### 3.3 Context drawer

Opens for **inspection**, not for **blocking action** (actions stay in stream).

| Drawer tab | IS content | OS content |
|------------|------------|------------|
| Files | Corpus list, wave/batch, virus scan status | — |
| Mapped | Per-file → doctype, column map, sample rows | — |
| Validate | Doctype table, errors/warnings, LER candidates | — |
| Plan | Import phases, blocked reasons | Command steps, payload JSON (read-only) |
| Result | Import phase outcomes | Execute result, ERP links |

### 3.4 Upload (`+`)

- Always visible in composer.  
- Adds files to **active corpus wave**; triggers `files_uploaded` (or unified `user_turn` with `kind: upload`).  
- No standalone Upload route in target state (legacy route redirects to shell with drawer → Files).

---

## 4. Gate renderer contract

One **active gate** per session. Backend publishes:

```typescript
interface ActiveGate {
  gate_id: string;           // stable id, e.g. "mapping_confirm", "validation_submit"
  kind: 'mcq' | 'upload' | 'confirm' | 'drawer' | 'chat_only';
  title: string;             // user-facing, max ~80 chars
  body?: string;             // markdown-lite, from presentation agent
  options?: { id: string; label: string }[];
  drawer?: 'mapped' | 'validate' | 'import_plan' | 'files';
  blocking: boolean;         // if true, pipeline waits on this gate
  workflow_signal: string;   // internal — UI maps option → signal payload
  expires_when?: string;     // stage that clears this gate
}
```

### 4.1 Mapping from current IS signals (transitional)

| Legacy signal / status | Gate `gate_id` | `kind` | User sees |
|------------------------|----------------|--------|-----------|
| `awaiting_f3iche_confirmation` | `f3iche_confirm` | `mcq` | “Is this your business type?” |
| `awaiting_data_readiness_confirmation` | `readiness_gap` | `upload` \| `mcq` | “Upload missing files” or “Continue without X” |
| `awaiting_mapping_confirmation` | `mapping_confirm` | `confirm` + `drawer:mapped` | “Approve mappings” after review |
| `awaiting_validation_submission` | `validation_submit` | `confirm` + `drawer:validate` | “Submit validation review” |
| `awaiting_import_confirmation` | `import_confirm` | `confirm` + `drawer:import_plan` | “Start import” |

**Rule:** Logs may say `validation_submitted`; banner must say **“Review validation and confirm”** — same event, user vocabulary.

### 4.2 OS gates (same renderer)

| OS state | `gate_id` | `kind` |
|----------|-----------|--------|
| `awaiting_clarification` | `os_clarify` | `mcq` |
| `semantic_confirm_required` | `os_confirm` | `confirm` |
| `resolution_gaps` with candidates | `os_resolve` | `mcq` |

---

## 5. API contracts (target)

### 5.1 `GET /api/session/{project_id}/agent-surface`

Returns everything the shell needs in **one poll** (replaces 4–5 parallel fetches):

```json
{
  "mode": "implementation",
  "stage": "awaiting_validation_submission",
  "active_gate": { "...": "ActiveGate" },
  "stream_messages": [],
  "sidebar_nodes": [],
  "drawer_default": "validate",
  "readiness_score": 86,
  "brain_version": "1.0"
}
```

### 5.2 `POST /api/session/{project_id}/user-turn`

Unified user action (collapses many signals over time):

```json
{
  "gate_id": "validation_submit",
  "kind": "confirm",
  "payload": { "approved": true },
  "chat_message": null
}
```

Or free chat:

```json
{
  "gate_id": null,
  "kind": "chat",
  "payload": {},
  "chat_message": "map Item_Consumed to stock line items"
}
```

Backend dispatches to existing Temporal signals during migration.

### 5.3 Polling rules

| State | Behavior |
|-------|----------|
| Background refresh | `refreshing: true` — **does not** disable composer |
| Initial load | Skeleton in stream only |
| Gate change | Prepend presentation agent message; update banner |

---

## 6. Presentation integration

- All **assistant-visible** copy in stream comes from [`PRESENTATION_AGENT_CONTRACT.md`](./PRESENTATION_AGENT_CONTRACT.md).  
- Drawer tables are **structured data** — no LLM required for row display.  
- Gate `title` / `body` / `options[].label` are presentation outputs.

---

## 7. Migration plan (phased)

### Phase 0 — Honesty hotfixes (days)

- [ ] Do not disable chat on poll (`loading` split)  
- [ ] Hide debug `summary_for_ui` from stream  
- [ ] Single banner on Analyze when `awaiting_validation_submission`

### Phase 1 — Shell scaffold (1–2 weeks)

- [ ] New layout route: `/[company]/[user]/workspace` (or embed in Implementation layout)  
- [ ] Sidebar + stream + drawer (empty drawer OK)  
- [ ] `GET agent-surface` stub aggregating existing endpoints

### Phase 2 — Gate renderer (1–2 weeks)

- [ ] Render `active_gate` for mapping + validation confirm  
- [ ] Drawer: validate preview from existing API  
- [ ] Deprecate duplicate PromptCard when gate active

### Phase 3 — Signal collapse (2 weeks)

- [ ] `user_turn` endpoint → existing signals  
- [ ] Remove parallel supervisor chat mirror for `ask_user`  
- [ ] Redirect legacy `/upload`, `/analyze`, `/validate`, `/import` to shell + drawer tab

### Phase 4 — OS parity (later)

- [ ] Same shell, OS mode tree  
- [ ] Shared composer + presentation agent

---

## 8. Deprecation list

Do **not** extend these; migrate and remove.

| Asset | Location (typical) | Replace with |
|-------|-------------------|--------------|
| `SupervisorPanel` parallel poll + synth cards | `frontend/.../supervisor/SupervisorPanel.tsx` | Agent stream + `agent-surface` |
| `PromptCard` duplicate of chat | `PromptCard.tsx` | Inline `mcq` gate renderer |
| `BrainVisualizer` “thinking” on user-wait | `analyze/BrainVisualizer` | Sidebar node `needs_you` |
| `readiness_summary` synth message | `SupervisorPanel` displayMessages | Gate banner + drawer |
| `gap_blocking` generic copy | `session_gaps.py` | Presentation agent + column detail |
| `summary_for_ui` in user chat | `persist_supervisor_prompt.py` | Presentation agent `body` |
| Quality gate `default_assumed` in stream | `quality_gate/activity.py` | Dev log only, or drawer → Logs tab |
| Four full-page IS steps as **primary** nav | `(Implementation)/*/page.tsx` | Sidebar nodes + drawer |
| 6+ separate Temporal signal UIs | various | `user_turn` + gate renderer |

**Keep (refactor in place):**

- `ValidateView` table logic → drawer tab  
- `ChatBar` / composer → always-on bottom of stream  
- `DeploymentPill`, project context  
- Import results honesty components (move to drawer Result tab)

---

## 9. Acceptance criteria (shell)

| ID | Test |
|----|------|
| SH-01 | User on `awaiting_validation_submission` sees banner “Review validation” — not “System is thinking” |
| SH-02 | Composer stays enabled during 4s background refresh |
| SH-03 | At most one MCQ/upload gate visible; answering clears gate |
| SH-04 | Mapped data review opens drawer — main stream unchanged |
| SH-05 | Green Surface 3rd_run loop completable without legacy-only pages (after Phase 3) |

---

## 10. Non-goals (this RFC)

- Full visual redesign / new design system  
- Mic / voice  
- Merging IS and OS Temporal workflows into one workflow type  
- Replacing KB with live-schema agent (v2)

---

*Implementation tracking: add rows to [`IS_V2_BACKLOG.md`](./IS_V2_BACKLOG.md) pillar 8–9; sprint cap in [`PRIORITIES.md`](./PRIORITIES.md).*
