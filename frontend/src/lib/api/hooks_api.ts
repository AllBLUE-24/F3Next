// src/lib/api/hooks_api.ts
import { getBaseApiUrl } from "@/lib/config";
const API_BASE_URL = getBaseApiUrl();

function formatApiError(detail: unknown, fallback: string): string {
  if (typeof detail === "string" && detail.trim()) return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) =>
        typeof item === "object" && item && "msg" in item
          ? String((item as { msg?: string }).msg)
          : String(item)
      )
      .join("; ");
  }
  if (detail && typeof detail === "object") {
    return JSON.stringify(detail);
  }
  return fallback;
}

// --- Discovery Chat (sync, ChatGPT-style) ---

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  ts?: string;
}

export interface DiscoverySessionResponse {
  messages: ChatMessage[];
  status: string;
  phase?: string;
  is_complete: boolean;
  is_finalized?: boolean;
  awaiting_confirmation?: boolean;
  awaiting_clarification?: boolean;
  clarifying_questions?: Array<Record<string, unknown>>;
  user_turns: number;
  ready_for_recommendation: boolean;
  discovery_metadata?: Record<string, unknown> | null;
  coverage?: Record<string, unknown> | null;
}

export interface DiscoveryChatResponse {
  reply: string;
  messages: ChatMessage[];
  status: string;
  is_complete: boolean;
  user_turns?: number;
  ready_for_recommendation?: boolean;
}

interface ChatPayload {
  project_id: string;
  message: string;
  step?: number;
}

export const getDiscoverySession = async (
  projectId: string
): Promise<DiscoverySessionResponse> => {
  const res = await fetch(`${API_BASE_URL}/api/discovery/session/${projectId}`, {
    cache: "no-store",
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to load session (${res.status})`);
  }
  return res.json();
};

export const sendMessageToDiscoveryAgent = async (
  payload: ChatPayload
): Promise<DiscoveryChatResponse> => {
  const res = await fetch(`${API_BASE_URL}/api/discovery/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    const errorDetail =
      typeof errorData.detail === "object"
        ? JSON.stringify(errorData.detail)
        : errorData.detail;
    throw new Error(errorDetail || `API Error: ${res.status}`);
  }
  return res.json();
};

export const completeDiscovery = async (
  projectId: string
): Promise<{
  status: string;
  phase?: string;
  data: Record<string, unknown>;
  confirmation_message?: string;
  workflow_preview?: Record<string, unknown>;
  clarifying_questions?: Array<Record<string, unknown>>;
  assurance?: Record<string, unknown>;
  closure_test?: string;
}> => {
  const res = await fetch(`${API_BASE_URL}/api/discovery/complete`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ project_id: projectId }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Complete failed (${res.status})`);
  }
  return res.json();
};

export const submitDiscoveryClarification = async (payload: {
  project_id: string;
  answers: Record<string, string | string[]>;
}): Promise<{
  status: string;
  phase?: string;
  data: Record<string, unknown>;
  confirmation_message?: string;
  workflow_preview?: Record<string, unknown>;
  clarifying_questions?: Array<Record<string, unknown>>;
  assurance?: Record<string, unknown>;
  closure_test?: string;
}> => {
  const res = await fetch(`${API_BASE_URL}/api/discovery/clarification`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(formatApiError(err.detail, `Clarification failed (${res.status})`));
  }
  return res.json();
};

export interface UploadColumnHint {
  field: string;
  label: string;
  synonyms?: string[];
  fieldtype?: string;
}

export interface UploadSchemaDoctype {
  required_columns: UploadColumnHint[];
  optional_columns: UploadColumnHint[];
  kb_available: boolean;
}

export interface ValidatorWarning {
  code?: string;
  message?: string;
  severity?: string;
  suggested_doctypes?: string[];
}

export interface WorkflowPreviewResponse {
  phase: string;
  workflow_explanation: Record<string, unknown>;
  seed_doctypes: string[];
  deferred_doctypes?: string[];
  required_doctypes: string[];
  promoted_doctypes?: string[];
  dual_system_note?: string;
  assurance?: { level?: string; reasons?: string[]; requires_acknowledgment?: boolean };
  closure_test?: string;
  promotion_labels?: Record<string, string>;
  validator_warnings?: ValidatorWarning[];
  upload_schema_preview?: Record<string, UploadSchemaDoctype>;
  discovery_metadata?: Record<string, unknown>;
}

export const getWorkflowPreview = async (
  projectId: string
): Promise<WorkflowPreviewResponse> => {
  const res = await fetch(`${API_BASE_URL}/api/discovery/${projectId}/workflow-preview`, {
    cache: "no-store",
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Workflow preview failed (${res.status})`);
  }
  return res.json();
};

export const confirmDiscoveryModules = async (payload: {
  project_id: string;
  confirmed_doctypes: string[];
  added_doctypes?: string[];
  removed_doctypes?: string[];
  notes?: string;
}): Promise<{ status: string; phase: string; data: Record<string, unknown> }> => {
  const res = await fetch(`${API_BASE_URL}/api/discovery/confirm-modules`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Confirm modules failed (${res.status})`);
  }
  return res.json();
};

// --- NEW CONFIG AGENT TYPES ---
export interface ConfigStatusResponse {
  status: string;
  layer: number;
  questions: any[];
  tags: string[];
}

export interface AnswerPayload {
  container_id: string;
  project_id: string;
  answers: Record<string, any>;
}

export const resolveProjectSlug = async (
  slug: string
): Promise<{ project_id: string; container_id?: string }> => {
  const res = await fetch(`${API_BASE_URL}/api/resolve/slug/${slug}`);
  if (!res.ok) throw new Error("Project not found");
  return res.json();
};

export const getConfigStatus = async (
  containerId: string
): Promise<ConfigStatusResponse> => {
  const res = await fetch(`${API_BASE_URL}/api/config/${containerId}/status`);
  if (!res.ok) throw new Error("Workflow not running");
  return res.json();
};

export const submitConfigAnswers = async (payload: AnswerPayload): Promise<void> => {
  const res = await fetch(`${API_BASE_URL}/api/config/answer`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to submit answers");
  }
};