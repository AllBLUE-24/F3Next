# Presentation Agent Contract

> **Status:** Contract — L0 LLM node for user-facing copy only  
> **Layer:** L5 (UX) + L1 (Honesty)  
> **IS pillar:** 8 (Supervisor presentation)  
> **Does not replace:** Temporal workflow decisions, mapping LLM, supervisor `auto_fix`  
> **Related:** [`NORTH_STAR_AGENT_SHELL.md`](./NORTH_STAR_AGENT_SHELL.md) · [`NORTH_STAR.md`](./NORTH_STAR.md)

---

## 1. Role

The **Presentation Agent** is a thin LLM (or deterministic formatter with optional LLM polish) that turns **canonical pipeline state** into **one clear user message** and **structured UI actions**.

It is analogous to how Cursor explains what it needs next — not dumping internal tool logs.

| Does | Does not |
|------|----------|
| Explain the **single active gate** in plain language | Decide whether mapping is correct |
| Propose MCQ labels and upload hints | Run `map_file_to_erpnext` |
| Summarize validation warnings for humans | Change validation verdict |
| Route free chat to intent handlers | Fire Temporal signals directly (API layer does) |

---

## 2. Placement in architecture

```text
Temporal workflow / activities
        │
        ▼
Canonical state (DB + R2) ──► Gate builder (deterministic)
        │                           │
        │                           ▼
        └──────────────────► Presentation Agent (L0 LLM)
                                    │
                                    ▼
                            Agent stream + ActiveGate JSON
                                    │
                                    ▼
                            user_turn API → signals
```

**Invocation points:**

- After `supervise_step` when `final_status=needs_user_input`  
- After `quality_gate` when `verdict=user_gap` (user-facing half only)  
- After mapping preflight block (`session_gaps`)  
- On user free chat (composer)  
- Optional: periodic “status nudge” when `blocking=true` and user idle

---

## 3. Inputs (strict schema)

```typescript
interface PresentationInput {
  project_id: string;
  mode: 'implementation' | 'operations';
  stage: string;                    // e.g. awaiting_validation_submission
  active_gate: ActiveGate | null;   // from shell contract
  gate_context: {
    gaps: GapItem[];                // shared/gate_contracts shape
    preflight_blocks?: {
      doctype: string;
      source_file: string;
      missing_fields: string[];
      column_hints?: Record<string, string>;  // CSV col → ERP field
    }[];
    readiness?: {
      score: number;
      critical_count: number;
      partial_doctypes: string[];
    };
    validation?: {
      overall: 'pass' | 'partial' | 'fail';
      error_count: number;
      warning_count: number;
      top_warnings: string[];       // max 5, humanized
    };
    mapping_summary?: {
      files_mapped: number;
      files_total: number;
      unmapped: { file: string; reason: string }[];
    };
  };
  f3iche_id?: string;
  industry?: string;
  user_locale?: string;             // default en
  conversation_tail?: Message[];    // last N stream messages, max 10
}
```

### 3.1 Required canonical fields (deterministic layer)

Before LLM, a **gate builder** MUST set:

- `active_gate.gate_id`  
- `active_gate.blocking`  
- `active_gate.workflow_signal`  
- `gate_context` from DB/R2 — never from LLM hallucination

LLM only fills **copy** fields.

---

## 4. Outputs (strict schema)

```typescript
interface PresentationOutput {
  stream_message: {
    role: 'assistant';
    content: string;              // markdown-lite, ≤ 1200 chars
    message_type: 'gate_prompt' | 'status' | 'answer';
  };
  active_gate_patch?: {
    title: string;
    body?: string;
    options?: { id: string; label: string }[];
  };
  drawer_suggestion?: 'mapped' | 'validate' | 'files' | 'import_plan' | null;
  chat_intent?: 'remap' | 'upload_intent' | 'answer_supervisor' | 'general_question';
  internal_debug?: string;        // NEVER sent to frontend in production
}
```

### 4.1 Copy rules

| Rule | Example |
|------|---------|
| One ask per message | “Upload stock movements” — not readiness + mapping + validate |
| Name the file and columns | “`stock_entry.csv`: map Item_Consumed → line item” |
| Say what happens next | “After you confirm, we’ll run import for orders and partners.” |
| Distinguish warning vs block | “7 warnings (missing ERP masters) — you can still proceed.” |
| No pipeline jargon | Never `assess_data_readiness`, `validation_submitted`, `Retrieved context blocks` |

---

## 5. Forbidden in user stream

These MUST NOT appear in `stream_message.content` or `active_gate_patch` shown to users:

| Forbidden | Source today | Fix |
|-----------|--------------|-----|
| `summary_for_ui` debug string | `supervise_step` | Log server-side only; presentation output replaces |
| Node names (`map_file_to_erpnext:`) | supervisor | Strip |
| `errors=N, warnings=M` alone | supervisor | Translate to human counts + meaning |
| `Retrieved context blocks: …` | RAG metadata | Dev panel only |
| “Fix column headers” without mapping | `session_gaps.py` | Use `column_hints` from golden manifest |
| Quality gate raw `analysis` | `quality_gate` | Only if rewritten for users |
| Duplicate gate (PromptCard + chat) | UI | Single `gate_prompt` message |

**Enforcement:** API strips fields matching `/^\w+:\s*status=/` and blocks publish of `internal_debug`.

---

## 6. Prompt skeleton (L0 LLM)

```
You are the F3Next Implementation Assistant presentation layer.

You receive CANONICAL_STATE (JSON). You do NOT invent missing fields or change verdicts.

Write:
1. stream_message.content — one short paragraph + bullet list if needed
2. active_gate_patch.title — ≤ 80 chars
3. active_gate_patch.options — labels only; ids come from canonical gate

Tone: direct, calm, no ERP jargon. User is a business owner, not a consultant.

CANONICAL_STATE:
{json}

Respond as JSON matching PresentationOutput. Omit internal_debug unless NODE_ENV=development.
```

**Model:** `gpt-4o-mini` via `shared_llm.generate_json`  
**Max tokens:** 800  
**Temperature:** 0.2  

After any L0 prompt change: `python -m shared.smoke_llm`

---

## 7. Deterministic fallbacks (LLM down)

If LLM fails, gate builder uses templates:

| `gate_id` | Template |
|-----------|----------|
| `readiness_gap` | “We’re missing data for **{doctype}**. Upload a file or continue without it.” |
| `mapping_confirm` | “Review mappings in the panel →, then approve to continue.” |
| `mapping_blocked` | “**{file}** couldn’t map to **{doctype}**: missing **{fields}**. {column_hint_sentence}” |
| `validation_submit` | “Validation finished with **{warnings} warnings**, no blocking errors. Review and confirm to import.” |
| `f3iche_confirm` | “We think your business is **{f3iche_label}**. Is that right?” |

`column_hint_sentence` from [`GOLDEN_MATRIX_MANIFEST.md`](./GOLDEN_MATRIX_MANIFEST.md) per file.

---

## 8. Free chat routing

Composer messages hit presentation agent with `chat_intent` classification (reuse [`is_chat_dispatcher.py`](../backend/app/services/is_chat_dispatcher.py) patterns):

| Intent | Action |
|--------|--------|
| `remap` | Queue mapping refinement; reply “We’ll re-run mapping for …” |
| `upload_intent` | Highlight `+` upload; open drawer Files |
| `answer_supervisor` | Map to active `gate_id` MCQ if match |
| `general_question` | RAG-backed answer; cite doctype/file from context |

Chat never blocks on background poll.

---

## 9. Migration from current supervisor chat mirror

| Current | Target |
|---------|--------|
| `persist_supervisor_prompt` → `save_chat_message(..., summary_for_ui)` | `save_chat_message(..., presentation.stream_message)` |
| `session_gaps` generic string | Call presentation with `preflight_blocks` + column_hints |
| `quality_gate` → chat for `ok` analysis | Suppress or dev-only |
| `SupervisorPanel` synth readiness | `agent-surface` + one presentation message |

**Code touchpoints (when implementing):**

- `containers/implementation/file_io/persist_supervisor_prompt.py`  
- `containers/implementation/is_common/session_gaps.py`  
- `shared/quality_gate/activity.py` (`_persist_gate_chat`)  
- `backend/app/api/...` new `presentation_turn` or inside `user_turn`  
- New: `containers/implementation/presentation_agent/` (activities + prompts)

---

## 10. Tests

| ID | Test |
|----|------|
| PA-01 | Given Stock Entry preflight input, output contains `Item_Consumed` — not “fix column headers” alone |
| PA-02 | Output never contains substring `Retrieved context blocks` |
| PA-03 | `validation_submit` partial → says warnings OK to proceed |
| PA-04 | LLM failure → deterministic fallback returns valid JSON |
| PA-05 | `smoke_llm` passes after prompt edit |

---

## 11. Non-goals

- Multi-turn debate between agents  
- Replacing supervisor `auto_fix` logic  
- Generating mapped payloads  
- OS execute planning (OS keeps clarity agent; presentation wraps OS clarify copy later)

---

*Presentation agent is the voice of the north star shell. Pipeline stays authoritative; users stop reading logs.*
