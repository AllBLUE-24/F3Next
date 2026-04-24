/**
 * lib/api/os-api.ts
 */

import { getBaseApiUrl } from "@/lib/config";


// ─── Types ────────────────────────────────────────────────────────────────────

export interface CommandRequest {
  prompt:           string;
  project_id:       string;
  company_id:       string;
  user_id:          string;
  erp_type?:        "erpnext" | "odoo";
  session_id?:      string;
  session_context?: string; 
  mode:             "execute" | "analyze" | "search"; // 🔴 NEW: Explicit mode sent to backend
}

export interface CommandDispatch {
  status:      "dispatched";
  workflow_id: string;
  session_id:  string;
}

export type AgentStep =
  | "clarity"
  | "awaiting_clarification"
  | "retrieving_context"
  | "planning"
  | "generating_payload"
  | "validating"
  | "validation_failed"
  | "awaiting_confirmation"
  | "executing"
  | "formatting"
  | "done"
  | "error"
  | "cancelled"
  | "";

export interface ConfirmationRequest {
  type:        "ambiguity" | "confirmation";
  question?:   string;
  round?:      number;
  risk_level?: "low" | "medium" | "high";
  preview?: {
    action_summary:   string;
    entities:         string[];
    warnings:         Array<{ field: string; message: string }>;
    auto_corrections: Array<{ field: string; corrected: string; reason: string }>;
  };
}

export interface WorkflowStatus {
  status:               AgentStep;
  confirmation_request: ConfirmationRequest | null;
  response?:            string | null;
}

export interface WorkflowResult {
  status:   "success" | "error" | "cancelled";
  response: string;
  result?:  Record<string, unknown>;
  errors?:  Array<{ field: string; message: string }>;
}

export interface HistorySession {
  id:          string;
  project_id:  string;
  workflow_id: string | null;
  status:      string;
  history:     Array<{ role: "user" | "assistant" | "system"; content: string }>;
  created_at:  string;
}

// ─── Fetch helper ─────────────────────────────────────────────────────────────

async function call<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const res = await fetch(`${getBaseApiUrl()}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  if (!res.ok) {
    const body = await res.text();
    let detail: string;
    try { detail = (JSON.parse(body) as { detail?: string }).detail ?? body; }
    catch { detail = body; }
    throw new Error(`[${res.status}] ${detail}`);
  }
  return res.json() as Promise<T>;
}

// ─── API ──────────────────────────────────────────────────────────────────────

export const submitCommand = (body: CommandRequest) =>
  call<CommandDispatch>("/api/os/command", { method: "POST", body: JSON.stringify(body) });

export const pollStatus = (id: string) =>
  call<WorkflowStatus>(`/api/os/status/${id}`);

export const fetchResult = (id: string) =>
  call<WorkflowResult>(`/api/os/result/${id}`);

export const confirmCommand = (id: string, decision: "confirm" | "cancel") =>
  call<void>(`/api/os/confirm/${id}`, {
    method: "POST",
    body: JSON.stringify({ decision }),
  });

export const answerClarification = (id: string, answer: string) =>
  call<void>(`/api/os/answer/${id}`, {
    method: "POST",
    body: JSON.stringify({ answer }),
  });

export const fetchSessions = (projectId: string) =>
  call<{ sessions: HistorySession[] }>(`/api/os/sessions/${projectId}`)
    .then((r) => r.sessions);