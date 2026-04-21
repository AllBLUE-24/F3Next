// src/lib/api/hooks_api.ts
const API_BASE_URL = "";

// 1. Define the Input Interface (What frontend sends)
interface ChatPayload {
  project_id: string;
  message: string;
  step?: number; // Optional for now, but good to have
}

interface DiscoveryResponse {
  step: number;
  message: string;
}

// --- NEW CONFIG AGENT TYPES ---
export interface ConfigStatusResponse {
  status: string;
  layer: number;
  questions: any[];
  tags: string[];
}

export interface AnswerPayload {
  container_id: string;
  project_id: string; // <--- The new requirement
  answers: Record<string, any>;
}

/**
 * Sends a user message to the Discovery Agent backend.
 * @param message - The user's input string
 * @param projectId - MUST be a valid UUID string from your database
 */
export const sendMessageToDiscoveryAgent = async (
  payload: ChatPayload
): Promise<DiscoveryResponse> => {
  try {
    const res = await fetch(`${API_BASE_URL}/api/discovery/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      // 2. Body is now clean because payload matches backend expectations
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const errorData = await res.json().catch(() => ({}));
      const errorDetail = typeof errorData.detail === 'object' 
        ? JSON.stringify(errorData.detail) 
        : errorData.detail;
        
      console.error("Backend Validation Error:", errorDetail);
      throw new Error(errorDetail || `API Error: ${res.status}`);
    }

    return await res.json();

  } catch (error) {
    console.error("Discovery Agent API Error:", error);
    // Return a fallback so the UI doesn't crash
    return { step: 0, message: "Connection error. Please try again." };
  }
};

// --- NEW CONFIG API HOOKS ---

export const resolveProjectSlug = async (slug: string): Promise<{ project_id: string, container_id?: string }> => {
  const res = await fetch(`${API_BASE_URL}/api/resolve/slug/${slug}`);
  if (!res.ok) throw new Error("Project not found");
  return await res.json();
};

export const getConfigStatus = async (containerId: string): Promise<ConfigStatusResponse> => {
  const res = await fetch(`${API_BASE_URL}/api/config/${containerId}/status`);
  if (!res.ok) throw new Error("Workflow not running");
  return await res.json();
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