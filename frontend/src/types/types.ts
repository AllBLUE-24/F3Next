/**
 * components/OS/types.ts
 * Shared types for all OS components.
 */

export type MessageRole = "user" | "assistant" | "system" | "error";

export interface LogEntry {
  id:        string;
  role:      MessageRole;
  content:   string;
  timestamp: Date;
  /** Optional: structured result data for ResultBlock */
  meta?: {
    docName?:   string;
    docType?:   string;
    total?:     string;
    erpLink?:   string;
    warnings?:  string[];
  };
}

export type UiPhase =
  | "idle"
  | "submitting"
  | "polling"
  | "awaiting_clarification"
  | "awaiting_confirmation"
  | "done"
  | "error"
  | "cancelled";

export const TERMINAL_PHASES: UiPhase[] = ["done", "error", "cancelled"];

export const PIPELINE_STEPS = [
  { key: "clarity",            label: "CLARITY"    },
  { key: "retrieving_context", label: "CONTEXT"    },
  { key: "planning",           label: "PLAN"       },
  { key: "generating_payload", label: "PAYLOAD"    },
  { key: "validating",         label: "VALIDATE"   },
  { key: "executing",          label: "EXECUTE"    },
  { key: "formatting",         label: "FORMAT"     },
] as const;

export type PipelineKey = typeof PIPELINE_STEPS[number]["key"];

export const STEP_STATUS: Record<string, string> = {
  clarity:                "Parsing your intent...",
  awaiting_clarification: "Waiting for your answer...",
  retrieving_context:     "Fetching company & ERP schema...",
  planning:               "Building execution plan...",
  generating_payload:     "Generating ERP payload...",
  validating:             "Validating schema & rules...",
  awaiting_confirmation:  "Awaiting your confirmation...",
  executing:              "Calling ERPNext API...",
  formatting:             "Formatting result...",
};

export function uid(): string {
  return Math.random().toString(36).slice(2, 10);
}