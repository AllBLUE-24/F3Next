// src/lib/api/hooks_api.ts
import { getBaseApiUrl } from "@/lib/config";
const API_BASE_URL = getBaseApiUrl();

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

export interface WorkflowPreviewResponse {
  phase: string;
  workflow_explanation: Record<string, unknown>;
  seed_doctypes: string[];
  deferred_doctypes?: string[];
  required_doctypes: string[];
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